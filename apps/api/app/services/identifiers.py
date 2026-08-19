from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, ValidationError
from app.models import Cable, Device, Location, Rack, StandardProfile

_SAFE = re.compile(r"[^A-Z0-9]+")


class _Strict(defaultdict[str, Any]):
    def __missing__(self, key: str) -> Any:
        raise ValidationError(f"Missing identifier template value: {key}")


def normalize_identifier_part(value: str) -> str:
    normalized = _SAFE.sub("-", value.strip().upper()).strip("-")
    if not normalized:
        raise ValidationError("Identifier component became empty after normalization")
    return normalized


def render_identifier(template: str, values: dict[str, Any]) -> str:
    normalized = {
        key: normalize_identifier_part(value) if isinstance(value, str) else value
        for key, value in values.items()
    }
    try:
        rendered = template.format_map(_Strict(lambda: None, normalized)).upper()
    except (KeyError, ValueError) as exc:
        raise ValidationError(f"Invalid identifier template: {exc}") from exc
    if len(rendered) > 180:
        raise ValidationError("Generated identifier exceeds 180 characters")
    return rendered


def get_active_profile(session: Session, tenant_id) -> StandardProfile:
    profile = session.scalar(
        select(StandardProfile).where(
            StandardProfile.tenant_id == tenant_id,
            StandardProfile.status == "active",
        )
    )
    if not profile:
        profile = session.scalar(
            select(StandardProfile).where(
                StandardProfile.tenant_id.is_(None),
                StandardProfile.standard_family == "TIA-606",
                StandardProfile.edition == "D",
                StandardProfile.status == "active",
            )
        )
    if not profile:
        raise ValidationError("No active standards profile configured")
    return profile


def generate_identifier(
    session: Session, *, tenant_id, object_type: str, values: dict[str, Any]
) -> str:
    profile = get_active_profile(session, tenant_id)
    template = profile.identifier_templates.get(object_type)
    if not template:
        raise ValidationError(f"No identifier template configured for {object_type}")
    identifier = render_identifier(template, values)
    model_by_type = {"location": Location, "rack": Rack, "device": Device, "cable": Cable}
    model = model_by_type.get(object_type)
    if model:
        column = Rack.rack_identifier if model is Rack else model.identifier
        exists = session.scalar(
            select(model.id).where(model.tenant_id == tenant_id, column == identifier)
        )
        if exists:
            raise ConflictError(f"Generated identifier already exists: {identifier}")
    return identifier
