from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_KEYS = (
    "tenant_id",
    "owner_id",
    "supervisor_id",
    "contractor_id",
    "project_id",
    "location_id",
    "rack_id",
    "cable_id",
    "work_order_id",
)


def parse(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-seed-idempotency.py FIRST SECOND")
    first = parse(Path(sys.argv[1]))
    second = parse(Path(sys.argv[2]))
    missing = [key for key in REQUIRED_KEYS if not first.get(key) or not second.get(key)]
    changed = [key for key in REQUIRED_KEYS if first.get(key) != second.get(key)]
    if missing or changed:
        raise SystemExit(f"seed idempotency failed: missing={missing}, changed={changed}")
    print("seed_idempotency=PASS stable_ids=" + ",".join(REQUIRED_KEYS))


if __name__ == "__main__":
    main()
