from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent
from app.security import Principal


def record_audit(
    session: Session,
    *,
    principal: Principal,
    action: str,
    object_type: str,
    object_id: uuid.UUID,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    project_id: uuid.UUID | None = None,
) -> AuditEvent:
    event = AuditEvent(
        tenant_id=principal.tenant_id,
        actor_id=principal.actor_id,
        actor_organization_id=principal.actor_organization_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        before=before,
        after=after,
        request_id=principal.request_id,
        ip_address=principal.ip_address,
        user_agent=principal.user_agent,
        project_id=project_id,
    )
    session.add(event)
    session.flush()
    return event
