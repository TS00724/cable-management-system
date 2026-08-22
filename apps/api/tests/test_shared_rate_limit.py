from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from app.config import Settings
from app.http_security import SecurityBoundaryMiddleware
from app.shared_rate_limit import (
    DatabaseFixedWindowRateLimiter,
    rate_limit_metadata,
    rate_limit_windows,
)


def test_database_limiter_shares_quota_and_hashes_identity(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'rate.db'}"
    engine = create_engine(database_url)
    rate_limit_metadata.create_all(engine)
    first = DatabaseFixedWindowRateLimiter(
        database_url=database_url,
        limit=2,
        window_seconds=60,
        key_secret="unit-secret",
    )
    second = DatabaseFixedWindowRateLimiter(
        database_url=database_url,
        limit=2,
        window_seconds=60,
        key_secret="unit-secret",
    )
    assert first.consume("tenant|actor|203.0.113.5", now=120).allowed is True
    assert second.consume("tenant|actor|203.0.113.5", now=120).allowed is True
    decision = first.consume("tenant|actor|203.0.113.5", now=120)
    assert decision.allowed is False
    assert decision.remaining == 0
    with engine.connect() as connection:
        row = connection.execute(select(rate_limit_windows)).one()
    assert row.key_hash != "tenant|actor|203.0.113.5"
    assert len(row.key_hash) == 64
    assert row.count == 3


def _app(settings: Settings) -> FastAPI:
    application = FastAPI()
    application.add_middleware(SecurityBoundaryMiddleware, settings=settings)

    @application.get("/resource")
    def resource() -> dict[str, bool]:
        return {"ok": True}

    return application


def test_rate_limit_backend_failure_modes() -> None:
    class BrokenLimiter:
        def consume(self, _key: str, *, now=None):
            raise RuntimeError("database unavailable")

    for mode, expected in (("closed", 503), ("open", 200)):
        application = _app(Settings(_env_file=None, rate_limit_fail_mode=mode))
        with TestClient(application) as client:
            middleware = client.app.middleware_stack.app
            middleware.limiter = BrokenLimiter()
            response = client.get("/resource")
            assert response.status_code == expected
            if mode == "open":
                assert response.headers["x-ratelimit-policy"] == "degraded-open"
