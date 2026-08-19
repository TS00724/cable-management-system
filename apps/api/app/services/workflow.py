from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.audit import record_audit
from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models import Cable, CableStatus, TestRecord, WorkOrder, WorkOrderStatus
from app.security import Principal, require_permission


class CableWorkflowService:
    def __init__(self, session: Session, principal: Principal):
        self.session = session
        self.principal = principal

    def mark_installed(
        self, cable_id: uuid.UUID, work_order_id: uuid.UUID | None = None
    ) -> Cable:
        require_permission(self.principal, "cable:install")
        cable = self.session.get(Cable, cable_id)
        if not cable:
            raise NotFoundError("Cable not found in tenant")
        allowed = {
            CableStatus.PLANNED,
            CableStatus.APPROVED,
            CableStatus.ORDERED,
            CableStatus.STAGED,
            CableStatus.TERMINATED,
        }
        if cable.installation_status not in allowed:
            raise ConflictError(f"Cable cannot be installed from {cable.installation_status.value}")
        before = cable.installation_status.value
        cable.installation_status = CableStatus.INSTALLED
        cable.installer_id = self.principal.actor_id
        cable.installed_at = datetime.now(UTC)
        if work_order_id:
            work_order = self.session.get(WorkOrder, work_order_id)
            if not work_order or work_order.cable_id not in {None, cable.id}:
                raise NotFoundError("Work order not found for cable in tenant")
            work_order.status = WorkOrderStatus.AWAITING_TEST
        record_audit(
            self.session,
            principal=self.principal,
            action="cable.installed",
            object_type="cable",
            object_id=cable.id,
            before={"status": before},
            after={"status": cable.installation_status.value},
            project_id=cable.project_id,
        )
        return cable

    def submit_test(
        self,
        *,
        cable_id: uuid.UUID,
        result: str,
        measurements: dict[str, Any],
        work_order_id: uuid.UUID | None = None,
        attachment_name: str | None = None,
    ) -> TestRecord:
        require_permission(self.principal, "cable:test")
        cable = self.session.get(Cable, cable_id)
        if not cable:
            raise NotFoundError("Cable not found in tenant")
        if cable.installation_status not in {
            CableStatus.INSTALLED,
            CableStatus.TERMINATED,
            CableStatus.TESTED,
        }:
            raise ConflictError("Cable must be installed or terminated before testing")
        normalized = result.upper()
        if normalized not in {"PASS", "FAIL"}:
            raise ValidationError("Test result must be PASS or FAIL")
        record = TestRecord(
            tenant_id=self.principal.tenant_id,
            cable_id=cable.id,
            work_order_id=work_order_id,
            tester_id=self.principal.actor_id,
            result=normalized,
            measurements=measurements,
            tested_at=datetime.now(UTC),
            attachment_name=attachment_name,
        )
        self.session.add(record)
        self.session.flush()
        cable.test_status = normalized
        cable.tested_at = record.tested_at
        cable.installation_status = CableStatus.TESTED
        if work_order_id:
            work_order = self.session.get(WorkOrder, work_order_id)
            if not work_order or work_order.cable_id not in {None, cable.id}:
                raise NotFoundError("Work order not found for cable in tenant")
            work_order.status = WorkOrderStatus.AWAITING_APPROVAL
        record_audit(
            self.session,
            principal=self.principal,
            action="cable.tested",
            object_type="test_record",
            object_id=record.id,
            after={"cable_id": str(cable.id), "result": normalized},
            project_id=cable.project_id,
        )
        return record

    def approve_test(self, test_record_id: uuid.UUID) -> TestRecord:
        require_permission(self.principal, "cable:approve")
        record = self.session.get(TestRecord, test_record_id)
        if not record:
            raise NotFoundError("Test record not found in tenant")
        if record.tester_id == self.principal.actor_id:
            raise ConflictError("A tester may not approve their own restricted test record")
        if record.status == "approved":
            return record
        cable = self.session.get(Cable, record.cable_id)
        if not cable:
            raise NotFoundError("Cable not found in tenant")
        if record.result != "PASS":
            raise ConflictError("Failed test records cannot commission a cable")
        record.status = "approved"
        record.approved_by = self.principal.actor_id
        record.approved_at = datetime.now(UTC)
        before = cable.installation_status.value
        cable.installation_status = CableStatus.IN_SERVICE
        if record.work_order_id:
            work_order = self.session.get(WorkOrder, record.work_order_id)
            if work_order:
                work_order.status = WorkOrderStatus.COMPLETED
        record_audit(
            self.session,
            principal=self.principal,
            action="cable.commissioned",
            object_type="cable",
            object_id=cable.id,
            before={"status": before},
            after={"status": cable.installation_status.value, "test_record": str(record.id)},
            project_id=cable.project_id,
        )
        return record
