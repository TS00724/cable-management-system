from __future__ import annotations

import csv
import io
import json

from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    client = TestClient(app)
    context_response = client.get("/api/v1/demo/context")
    context_response.raise_for_status()
    context = context_response.json()
    headers = {
        "X-Tenant-ID": context["tenant_id"],
        "X-Actor-ID": context["owner_id"],
    }
    export = client.get("/api/v1/reports/cable-schedule.csv", headers=headers)
    export.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(export.content.decode("utf-8-sig"))))
    if not rows:
        raise RuntimeError("Seeded cable schedule export returned no rows")
    audits = client.get("/api/v1/audit-events", headers=headers)
    audits.raise_for_status()
    export_events = [
        event
        for event in audits.json()["items"]
        if event["action"] == "report.cable_schedule.exported"
    ]
    if not export_events:
        raise RuntimeError("Cable schedule export audit event was not persisted")
    print(
        json.dumps(
            {
                "rows": len(rows),
                "first_identifier": rows[0]["Cable Identifier"],
                "content_type": export.headers.get("content-type"),
                "audit_events": len(export_events),
                "truncated": export.headers.get("x-export-truncated"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
