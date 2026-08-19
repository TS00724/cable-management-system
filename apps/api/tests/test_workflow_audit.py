import pytest
from sqlalchemy import select

from app.exceptions import AuthorizationError, ConflictError
from app.models import AuditEvent, Cable, CableStatus, TestRecord as CableTestRecord
from app.security import resolve_principal
from app.services.workflow import CableWorkflowService


def test_install_test_approve_workflow_is_segregated_and_audited(world) -> None:
    with world.scoped_session() as session:
        contractor = resolve_principal(
            session,
            actor_id=world.contractor,
            tenant_id=world.tenant_a,
            project_id=world.project,
            location_id=world.tr,
        )
        workflow = CableWorkflowService(session, contractor)
        workflow.mark_installed(world.horizontal_cable)
        record = workflow.submit_test(
            cable_id=world.horizontal_cable,
            result="PASS",
            measurements={"wiremap": "PASS", "length_m": 22.4},
        )
        with pytest.raises(AuthorizationError, match="Missing permission"):
            workflow.approve_test(record.id)
        session.commit()

    with world.scoped_session() as session:
        supervisor = resolve_principal(
            session,
            actor_id=world.supervisor,
            tenant_id=world.tenant_a,
            project_id=world.project,
            location_id=world.tr,
        )
        record = session.scalar(
            select(CableTestRecord).where(CableTestRecord.cable_id == world.horizontal_cable)
        )
        CableWorkflowService(session, supervisor).approve_test(record.id)
        session.commit()

    with world.scoped_session() as session:
        cable = session.get(Cable, world.horizontal_cable)
        assert cable.installation_status == CableStatus.IN_SERVICE
        actions = {
            event.action
            for event in session.scalars(
                select(AuditEvent).where(AuditEvent.object_id == world.horizontal_cable)
            )
        }
        assert {"cable.created", "cable.installed", "cable.commissioned"}.issubset(actions)


def test_approver_cannot_approve_own_test(world) -> None:
    with world.scoped_session() as session:
        admin = resolve_principal(
            session,
            actor_id=world.admin,
            tenant_id=world.tenant_a,
            project_id=world.project,
            location_id=world.tr,
        )
        workflow = CableWorkflowService(session, admin)
        workflow.mark_installed(world.horizontal_cable)
        record = workflow.submit_test(
            cable_id=world.horizontal_cable, result="PASS", measurements={"wiremap": "PASS"}
        )
        with pytest.raises(ConflictError, match="may not approve"):
            workflow.approve_test(record.id)


def test_failed_test_cannot_be_approved(world) -> None:
    with world.scoped_session() as session:
        admin = resolve_principal(
            session,
            actor_id=world.admin,
            tenant_id=world.tenant_a,
            project_id=world.project,
            location_id=world.tr,
        )
        workflow = CableWorkflowService(session, admin)
        workflow.mark_installed(world.horizontal_cable)
        record = workflow.submit_test(
            cable_id=world.horizontal_cable, result="FAIL", measurements={"wiremap": "FAIL"}
        )
        supervisor = resolve_principal(
            session,
            actor_id=world.supervisor,
            tenant_id=world.tenant_a,
            project_id=world.project,
            location_id=world.tr,
        )
        with pytest.raises(ConflictError, match="Failed test"):
            CableWorkflowService(session, supervisor).approve_test(record.id)


def test_audit_events_are_immutable(world) -> None:
    with world.scoped_session() as session:
        event = session.scalar(select(AuditEvent).limit(1))
        event.action = "tampered"
        with pytest.raises(PermissionError, match="immutable"):
            session.flush()
