import pytest
from sqlalchemy import select

from app.exceptions import ConflictError, ValidationError
from app.models import Device, Port
from app.security import resolve_principal
from app.services.connectivity import ConnectivityService


def test_trace_crosses_patch_panel_internal_mapping(world) -> None:
    with world.scoped_session() as session:
        principal = resolve_principal(session, actor_id=world.admin, tenant_id=world.tenant_a)
        trace = ConnectivityService(session, principal).trace_cable(world.horizontal_cable)
    kinds = [item["kind"] for item in trace["items"]]
    assert kinds == ["port", "cable", "port", "internal_mapping", "port", "cable", "port"]
    identifiers = {item.get("identifier") for item in trace["items"]}
    assert "A-MC-ENG-TR01-HC-00001" in identifiers
    assert "A-MC-ENG-TR01-PC-00001" in identifiers
    assert trace["complete"] is True


def test_port_cannot_be_terminated_twice(world) -> None:
    with world.scoped_session() as session:
        principal = resolve_principal(session, actor_id=world.admin, tenant_id=world.tenant_a)
        switch = session.get(Device, world.switch)
        panel = session.get(Device, world.panel)
        occupied = session.scalar(
            select(Port).where(Port.device_id == switch.id, Port.identifier == "G01")
        )
        spare = session.scalar(
            select(Port).where(Port.device_id == panel.id, Port.identifier == "F02")
        )
        with pytest.raises(ConflictError, match="already physically terminated"):
            ConnectivityService(session, principal).create_cable(
                identifier="A-MC-ENG-TR01-PC-00002",
                media_type="Cat6A copper",
                construction="patch_cord",
                port_a_id=occupied.id,
                port_b_id=spare.id,
                project_id=world.project,
            )


def test_media_compatibility_is_enforced(world) -> None:
    with world.scoped_session() as session:
        principal = resolve_principal(session, actor_id=world.admin, tenant_id=world.tenant_a)
        ports = session.scalars(select(Port).limit(2)).all()
        with pytest.raises(ValidationError, match="incompatible"):
            ConnectivityService(session, principal)._validate_ports_for_cable(
                "OS2 fiber", ports[0], ports[1]
            )
