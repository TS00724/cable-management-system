from fastapi.testclient import TestClient

from app.api import deps
from app.main import app


def test_api_trace_rack_and_cross_tenant_isolation(world, monkeypatch) -> None:
    monkeypatch.setattr(deps, "SessionLocal", world.session_factory)
    monkeypatch.setattr(deps, "PlatformSessionLocal", world.session_factory)
    client = TestClient(app)
    headers = {"X-Tenant-ID": str(world.tenant_a), "X-Actor-ID": str(world.admin)}
    trace = client.get(f"/api/v1/cables/{world.horizontal_cable}/trace", headers=headers)
    assert trace.status_code == 200
    assert trace.json()["complete"] is True
    elevation = client.get(f"/api/v1/racks/{world.rack}/elevation", headers=headers)
    assert elevation.status_code == 200
    assert elevation.json()["rack"]["identifier"] == "A-MC-ENG-TR01-R01"
    private = client.get(f"/api/v1/racks/{world.private_rack}/elevation", headers=headers)
    assert private.status_code == 404


def test_api_generates_qr_label(world, monkeypatch) -> None:
    monkeypatch.setattr(deps, "SessionLocal", world.session_factory)
    monkeypatch.setattr(deps, "PlatformSessionLocal", world.session_factory)
    client = TestClient(app)
    headers = {"X-Tenant-ID": str(world.tenant_a), "X-Actor-ID": str(world.admin)}
    response = client.post(f"/api/v1/labels/cables/{world.horizontal_cable}", headers=headers)
    assert response.status_code == 201
    assert str(world.horizontal_cable) in response.json()["qr_payload"]
    assert "<svg" in response.json()["qr_svg"]


def test_api_contractor_install_test_and_supervisor_approval(world, monkeypatch) -> None:
    monkeypatch.setattr(deps, "SessionLocal", world.session_factory)
    monkeypatch.setattr(deps, "PlatformSessionLocal", world.session_factory)
    client = TestClient(app)
    contractor_headers = {
        "X-Tenant-ID": str(world.tenant_a),
        "X-Actor-ID": str(world.contractor),
        "X-Project-ID": str(world.project),
        "X-Location-ID": str(world.tr),
    }
    installed = client.post(
        f"/api/v1/cables/{world.horizontal_cable}/install", headers=contractor_headers
    )
    assert installed.status_code == 200
    assert installed.json()["installation_status"] == "installed"
    tested = client.post(
        f"/api/v1/cables/{world.horizontal_cable}/tests",
        headers=contractor_headers,
        json={"result": "PASS", "measurements": {"wiremap": "PASS", "length_m": 22.4}},
    )
    assert tested.status_code == 201
    test_id = tested.json()["id"]
    listed = client.get(
        f"/api/v1/test-results?cable_id={world.horizontal_cable}", headers=contractor_headers
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == test_id
    supervisor_headers = {
        "X-Tenant-ID": str(world.tenant_a),
        "X-Actor-ID": str(world.supervisor),
        "X-Project-ID": str(world.project),
        "X-Location-ID": str(world.tr),
    }
    approved = client.post(f"/api/v1/tests/{test_id}/approve", headers=supervisor_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_api_security_headers_are_present(world, monkeypatch) -> None:
    monkeypatch.setattr(deps, "SessionLocal", world.session_factory)
    monkeypatch.setattr(deps, "PlatformSessionLocal", world.session_factory)
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'self'" in response.headers["content-security-policy"]


def test_web_application_static_assets_are_served() -> None:
    client = TestClient(app)
    page = client.get("/app/")
    assert page.status_code == 200
    assert "Structured Infrastructure Manager" in page.text
    assert 'id="export-cables"' in page.text
    script = client.get("/app/app.js")
    assert script.status_code == 200
    assert "Infrastructure3DViewer" in script.text
    assert "downloadCableSchedule" in script.text
    viewer = client.get("/app/webgl-viewer.js")
    assert viewer.status_code == 200
    assert "class Infrastructure3DViewer" in viewer.text
