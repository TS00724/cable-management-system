from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.exceptions import AuthorizationError
from app.models import AccessGrant
from app.security import resolve_principal


def test_contractor_grant_allows_matching_project_and_descendant_location(world) -> None:
    with world.scoped_session() as session:
        principal = resolve_principal(
            session,
            actor_id=world.contractor,
            tenant_id=world.tenant_a,
            project_id=world.project,
            location_id=world.tr,
        )
        assert "cable:test" in principal.permissions
        assert principal.is_tenant_member is False


def test_contractor_grant_denies_out_of_scope_location(world) -> None:
    with world.scoped_session() as session:
        with pytest.raises(AuthorizationError):
            resolve_principal(
                session,
                actor_id=world.contractor,
                tenant_id=world.tenant_a,
                project_id=world.project,
                location_id=world.other_building,
            )


def test_expired_grant_is_denied(world) -> None:
    with world.scoped_session() as session:
        grant = session.scalar(select(AccessGrant).where(AccessGrant.project_id == world.project))
        grant.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
        with pytest.raises(AuthorizationError):
            resolve_principal(
                session,
                actor_id=world.contractor,
                tenant_id=world.tenant_a,
                project_id=world.project,
                location_id=world.tr,
            )
