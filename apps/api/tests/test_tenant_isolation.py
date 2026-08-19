import pytest
from sqlalchemy import select

from app.models import Rack


def test_scoped_query_hides_other_tenant_rows(world) -> None:
    with world.scoped_session(world.tenant_a) as session:
        visible = session.scalars(select(Rack)).all()
        assert {rack.id for rack in visible} == {world.rack}
        assert session.get(Rack, world.private_rack) is None


def test_cross_tenant_write_is_rejected(world) -> None:
    with world.scoped_session(world.tenant_a) as session:
        session.add(
            Rack(
                tenant_id=world.tenant_b,
                location_id=world.tr,
                rack_identifier="ILLEGAL-RACK",
                name="Illegal",
                height_u=42,
            )
        )
        with pytest.raises(PermissionError, match="Cross-tenant write rejected"):
            session.flush()
