from __future__ import annotations

import hashlib
import hmac
import threading
import time
from dataclasses import dataclass

from sqlalchemy import (
    BigInteger,
    Column,
    Engine,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


rate_limit_metadata = MetaData()
rate_limit_windows = Table(
    "rate_limit_windows",
    rate_limit_metadata,
    Column("key_hash", String(64), primary_key=True),
    Column("window_start_epoch", BigInteger, primary_key=True),
    Column("count", Integer, nullable=False),
    Column("expires_at_epoch", BigInteger, nullable=False),
    Index("ix_rate_limit_window_expires", "expires_at_epoch"),
)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_epoch: int


class FixedWindowRateLimiter:
    """Thread-safe in-process limiter for local development and unit tests."""

    def __init__(self, *, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[int, int]] = {}

    def consume(self, key: str, *, now: float | None = None) -> RateLimitDecision:
        timestamp = now if now is not None else time.time()
        window_start = int(timestamp // self.window_seconds) * self.window_seconds
        reset_epoch = window_start + self.window_seconds
        with self._lock:
            previous = self._windows.get(key)
            count = previous[1] if previous and previous[0] == window_start else 0
            count += 1
            self._windows[key] = (window_start, count)
            if len(self._windows) > 10_000:
                stale_before = window_start - self.window_seconds
                self._windows = {
                    item_key: item for item_key, item in self._windows.items() if item[0] >= stale_before
                }
        return RateLimitDecision(
            allowed=count <= self.limit,
            limit=self.limit,
            remaining=max(self.limit - count, 0),
            reset_epoch=reset_epoch,
        )


class DatabaseFixedWindowRateLimiter:
    """Shared fixed-window limiter using an atomic SQL upsert.

    Tenant, actor and IP values are HMAC-SHA256 pseudonymized before persistence.
    """

    def __init__(
        self,
        *,
        database_url: str,
        limit: int,
        window_seconds: int,
        key_secret: str,
        retention_seconds: int = 3600,
        cleanup_interval_seconds: int = 60,
        engine: Engine | None = None,
    ) -> None:
        if not key_secret:
            raise ValueError("A rate-limit key secret is required")
        self.limit = limit
        self.window_seconds = window_seconds
        self.key_secret = key_secret.encode("utf-8")
        self.retention_seconds = retention_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine = engine or create_engine(
            database_url, future=True, pool_pre_ping=True, connect_args=connect_args
        )
        self._cleanup_lock = threading.Lock()
        self._last_cleanup = 0.0

    def _hash_key(self, key: str) -> str:
        return hmac.new(self.key_secret, key.encode("utf-8"), hashlib.sha256).hexdigest()

    def _cleanup(self, *, now: float) -> None:
        if now - self._last_cleanup < self.cleanup_interval_seconds:
            return
        with self._cleanup_lock:
            if now - self._last_cleanup < self.cleanup_interval_seconds:
                return
            with self.engine.begin() as connection:
                connection.execute(
                    delete(rate_limit_windows).where(
                        rate_limit_windows.c.expires_at_epoch <= int(now)
                    )
                )
            self._last_cleanup = now

    def consume(self, key: str, *, now: float | None = None) -> RateLimitDecision:
        timestamp = now if now is not None else time.time()
        window_start = int(timestamp // self.window_seconds) * self.window_seconds
        reset_epoch = window_start + self.window_seconds
        expires_at = reset_epoch + self.retention_seconds
        key_hash = self._hash_key(key)
        table = rate_limit_windows

        with self.engine.begin() as connection:
            values = {
                "key_hash": key_hash,
                "window_start_epoch": window_start,
                "count": 1,
                "expires_at_epoch": expires_at,
            }
            if connection.dialect.name == "postgresql":
                statement = pg_insert(table).values(**values).on_conflict_do_update(
                    index_elements=[table.c.key_hash, table.c.window_start_epoch],
                    set_={"count": table.c.count + 1, "expires_at_epoch": expires_at},
                ).returning(table.c.count)
                count = int(connection.execute(statement).scalar_one())
            elif connection.dialect.name == "sqlite":
                statement = sqlite_insert(table).values(**values).on_conflict_do_update(
                    index_elements=[table.c.key_hash, table.c.window_start_epoch],
                    set_={"count": table.c.count + 1, "expires_at_epoch": expires_at},
                )
                connection.execute(statement)
                count = int(
                    connection.execute(
                        select(table.c.count).where(
                            table.c.key_hash == key_hash,
                            table.c.window_start_epoch == window_start,
                        )
                    ).scalar_one()
                )
            else:
                existing = connection.execute(
                    select(table.c.count).where(
                        table.c.key_hash == key_hash,
                        table.c.window_start_epoch == window_start,
                    ).with_for_update()
                ).scalar_one_or_none()
                if existing is None:
                    connection.execute(table.insert().values(**values))
                    count = 1
                else:
                    count = int(existing) + 1
                    connection.execute(
                        table.update().where(
                            table.c.key_hash == key_hash,
                            table.c.window_start_epoch == window_start,
                        ).values(count=count, expires_at_epoch=expires_at)
                    )

        self._cleanup(now=timestamp)
        return RateLimitDecision(
            allowed=count <= self.limit,
            limit=self.limit,
            remaining=max(self.limit - count, 0),
            reset_epoch=reset_epoch,
        )
