from sqlalchemy import select

from app.models import Label
from app.security import resolve_principal
from app.services.compliance import ComplianceService
from app.services.labels import LabelService


def test_qr_label_points_to_permission_protected_app_route(world) -> None:
    with world.scoped_session() as session:
        principal = resolve_principal(session, actor_id=world.admin, tenant_id=world.tenant_a)
        label, svg = LabelService(session, principal).create_cable_label(
            world.horizontal_cable, "https://sim.example"
        )
        assert str(world.horizontal_cable) in label.qr_payload
        assert label.qr_payload.startswith("https://sim.example/app/")
        assert "<svg" in svg
        assert session.scalar(select(Label).where(Label.id == label.id))


def test_compliance_report_identifies_unlabelled_objects(world) -> None:
    with world.scoped_session() as session:
        principal = resolve_principal(session, actor_id=world.admin, tenant_id=world.tenant_a)
        report = ComplianceService(session, principal).report()
        assert report["profile"]["edition"] == "D"
        assert report["summary"]["checked"] > 0
        assert any(item["type"] == "missing_label" for item in report["findings"])
        assert "not a legal certification" in report["legal_notice"]
