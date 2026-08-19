import pytest

from app.exceptions import ConflictError
from app.security import resolve_principal
from app.services.infrastructure import InfrastructureService


def test_rack_elevation_reports_persisted_devices_and_capacity(world) -> None:
    with world.scoped_session() as session:
        principal = resolve_principal(session, actor_id=world.admin, tenant_id=world.tenant_a)
        elevation = InfrastructureService(session, principal).rack_elevation(world.rack)
        assert elevation["rack"]["height_u"] == 42
        assert {item["identifier"] for item in elevation["devices"]} == {
            "A-MC-ENG-TR01-PP01",
            "A-MC-ENG-TR01-SW01",
        }
        assert elevation["capacity"]["used_u"] == 2
        assert elevation["capacity"]["reserved_u"] == 1


def test_overlapping_rack_device_is_rejected(world) -> None:
    with world.scoped_session() as session:
        principal = resolve_principal(session, actor_id=world.admin, tenant_id=world.tenant_a)
        with pytest.raises(ConflictError, match="overlaps"):
            InfrastructureService(session, principal).create_device_from_template(
                rack_id=world.rack,
                template_id=world.switch_template,
                identifier="A-MC-ENG-TR01-SW02",
                name="Overlap",
                start_u=38,
            )


def test_reserved_rack_u_is_rejected(world) -> None:
    with world.scoped_session() as session:
        principal = resolve_principal(session, actor_id=world.admin, tenant_id=world.tenant_a)
        with pytest.raises(ConflictError, match="reserved"):
            InfrastructureService(session, principal).create_device_from_template(
                rack_id=world.rack,
                template_id=world.switch_template,
                identifier="A-MC-ENG-TR01-SW03",
                name="Reserved",
                start_u=39,
            )
