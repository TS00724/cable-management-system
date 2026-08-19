from __future__ import annotations

import uuid
from collections.abc import Generator

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.db import PlatformSessionLocal, SessionLocal, set_platform_bypass, set_postgres_tenant_context
from app.security import Principal, resolve_principal


def get_platform_db() -> Generator[Session, None, None]:
    session = PlatformSessionLocal()
    set_platform_bypass(session)
    try:
        yield session
    finally:
        session.close()


def get_db(
    x_tenant_id: uuid.UUID = Header(alias="X-Tenant-ID"),
) -> Generator[Session, None, None]:
    session = SessionLocal()
    set_postgres_tenant_context(session, x_tenant_id)
    try:
        yield session
    finally:
        session.close()


def get_principal(
    request: Request,
    db: Session = Depends(get_db),
    x_tenant_id: uuid.UUID = Header(alias="X-Tenant-ID"),
    x_actor_id: uuid.UUID = Header(alias="X-Actor-ID"),
    x_project_id: uuid.UUID | None = Header(default=None, alias="X-Project-ID"),
    x_location_id: uuid.UUID | None = Header(default=None, alias="X-Location-ID"),
) -> Principal:
    return resolve_principal(
        db,
        actor_id=x_actor_id,
        tenant_id=x_tenant_id,
        project_id=x_project_id,
        location_id=x_location_id,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
