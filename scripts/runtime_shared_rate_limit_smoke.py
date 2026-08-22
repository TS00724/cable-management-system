from __future__ import annotations

import json
import multiprocessing
import tempfile
from pathlib import Path

from sqlalchemy import create_engine

from app.shared_rate_limit import (
    DatabaseFixedWindowRateLimiter,
    rate_limit_metadata,
)


def consume(database_url: str, output) -> None:  # type: ignore[no-untyped-def]
    limiter = DatabaseFixedWindowRateLimiter(
        database_url=database_url,
        limit=3,
        window_seconds=30,
        key_secret="runtime-shared-secret",
        retention_seconds=300,
        cleanup_interval_seconds=60,
    )
    result = limiter.consume("tenant|actor|203.0.113.10", now=120.0)
    output.put({"allowed": result.allowed, "remaining": result.remaining})


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="sim-rate-") as directory:
        database_url = f"sqlite+pysqlite:///{Path(directory) / 'rate.db'}"
        rate_limit_metadata.create_all(create_engine(database_url))
        context = multiprocessing.get_context("fork")
        output = context.Queue()
        results: list[dict[str, bool | int]] = []
        for _ in range(4):
            process = context.Process(target=consume, args=(database_url, output))
            process.start()
            process.join(timeout=30)
            if process.exitcode != 0:
                raise RuntimeError(f"rate-limit worker failed with exit code {process.exitcode}")
            results.append(output.get(timeout=5))
        assert [item["remaining"] for item in results] == [2, 1, 0, 0]
        assert [item["allowed"] for item in results] == [True, True, True, False]
        print(json.dumps({"shared_atomic_rate_limit": "PASS", "processes": results}, sort_keys=True))


if __name__ == "__main__":
    main()
