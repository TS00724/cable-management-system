from __future__ import annotations

import csv
import io

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api import deps
from app.main import app
from app.models import AuditEvent, Cable


def _client(world, monkeypatch) -> TestClient:
    monkeypatch.setattr(deps, "SessionLocal", world.session_factory)
    monkeypatch.setattr(deps, "PlatformSessionLocal", world.session_factory)
    return TestClient(app)


def _owner_headers(world) -> dict[str, str]:
    return {"X-Tenant-ID": str(world.tenant_a), "X-Actor-ID": str(world.admin)}


def _contractor_headers(world) -> dict[str, str]:
    return {
        "X-Tenant-ID": str(world.tenant_a),
        "X-Actor-ID": str(world.contractor),
        "X-Project-ID": str(world.project),
        "X-Location-ID": str(world.tr),
    }


def _csv_rows(response) -> list[dict[str, str]]:
    text = response.content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def test_cable_schedule_csv_exports_real_endpoints_and_audits(world, monkeypatch) -> None:
    client = _client(world, monkeypatch)
    response = client.get("/api/v1/reports/cable-schedule.csv", headers=_owner_headers(world))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["cache-control"] == "no-store"
    assert "attachment;" in response.headers["content-disposition"]
    assert response.headers["x-export-row-count"] == "2"
    assert response.headers["x-export-total-count"] == "2"
    assert response.headers["x-export-truncated"] == "false"

    rows = _csv_rows(response)
    identifiers = [row["Cable Identifier"] for row in rows]
    assert identifiers == ["A-MC-ENG-TR01-HC-00001", "A-MC-ENG-TR01-PC-00001"]

    horizontal = next(row for row in rows if row["Cable Identifier"].endswith("HC-00001"))
    assert horizontal["A Location Path"] == "A-MC / A-MC-ENG / A-MC-ENG-TR01"
    assert horizontal["A Device"] == "A-MC-ENG-TR01-PP01"
    assert horizontal["A Device Name"] == "Patch Panel"
    assert horizontal["A Port"] == "R01"
    assert horizontal["B Location Path"] == "A-MC / A-MC-ENG"
    assert horizontal["B Device"] == "A-MC-ENG-WA-001"
    assert horizontal["B Port"] == "A"
    assert horizontal["Project Number"] == "P-100"

    with world.scoped_session() as session:
        event = session.scalar(
            select(AuditEvent).where(AuditEvent.action == "report.cable_schedule.exported")
        )
        assert event is not None
        assert event.object_type == "cable_schedule"
        assert event.after["row_count"] == 2
        assert event.after["total_count"] == 2
        assert event.after["truncated"] is False
        assert event.after["format"] == "csv"


def test_cable_schedule_csv_is_tenant_scoped(world, monkeypatch) -> None:
    with world.session_factory() as session:
        session.info["bypass_tenant"] = True
        session.add(
            Cable(
                tenant_id=world.tenant_b,
                identifier="TENANT-B-SECRET-CABLE",
                media_type="OS2 fiber",
                construction="backbone",
            )
        )
        session.commit()

    client = _client(world, monkeypatch)
    response = client.get("/api/v1/reports/cable-schedule.csv", headers=_owner_headers(world))

    assert response.status_code == 200
    assert "TENANT-B-SECRET-CABLE" not in response.content.decode("utf-8-sig")
    assert response.headers["x-export-row-count"] == "2"
    assert response.headers["x-export-total-count"] == "2"


def test_cable_schedule_csv_supports_filters_limit_and_truncation(world, monkeypatch) -> None:
    client = _client(world, monkeypatch)
    response = client.get(
        (
            f"/api/v1/reports/cable-schedule.csv?project_id={world.project}"
            "&status=planned&q=Cat6A&limit=1"
        ),
        headers=_owner_headers(world),
    )

    assert response.status_code == 200
    rows = _csv_rows(response)
    assert len(rows) == 1
    assert rows[0]["Installation Status"] == "planned"
    assert rows[0]["Project Number"] == "P-100"
    assert response.headers["x-export-row-count"] == "1"
    assert response.headers["x-export-total-count"] == "2"
    assert response.headers["x-export-truncated"] == "true"


def test_cable_schedule_csv_rejects_missing_or_scoped_export_permission(
    world, monkeypatch
) -> None:
    client = _client(world, monkeypatch)

    supervisor = client.get(
        "/api/v1/reports/cable-schedule.csv",
        headers={"X-Tenant-ID": str(world.tenant_a), "X-Actor-ID": str(world.supervisor)},
    )
    contractor = client.get(
        "/api/v1/reports/cable-schedule.csv",
        headers=_contractor_headers(world),
    )

    assert supervisor.status_code == 403
    assert contractor.status_code == 403
    assert "report:export" in supervisor.json()["detail"]
    assert "report:export" in contractor.json()["detail"]


def test_cable_schedule_csv_neutralizes_spreadsheet_formulas(world, monkeypatch) -> None:
    with world.scoped_session() as session:
        cable = session.get(Cable, world.horizontal_cable)
        assert cable is not None
        cable.manufacturer = '=HYPERLINK("https://invalid.example","click")'
        session.commit()

    client = _client(world, monkeypatch)
    response = client.get(
        "/api/v1/reports/cable-schedule.csv?q=HC-00001",
        headers=_owner_headers(world),
    )

    assert response.status_code == 200
    rows = _csv_rows(response)
    assert len(rows) == 1
    assert rows[0]["Manufacturer"].startswith("'=HYPERLINK")
