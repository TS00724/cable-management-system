from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    AccessGrant,
    AccessGrantStatus,
    Cable,
    CableStatus,
    Device,
    Location,
    LocationType,
    Rack,
    TestRecord,
    WorkOrder,
    WorkOrderStatus,
)
from app.security import Principal, require_permission


class ReportingService:
    def __init__(self, session: Session, principal: Principal):
        self.session = session
        self.principal = principal

    def dashboard(self) -> dict[str, Any]:
        require_permission(self.principal, "dashboard:read")
        counts = {
            "buildings": self.session.scalar(
                select(func.count(Location.id)).where(Location.location_type == LocationType.BUILDING)
            ) or 0,
            "telecom_rooms": self.session.scalar(
                select(func.count(Location.id)).where(
                    Location.location_type.in_(
                        [LocationType.TR, LocationType.MDF, LocationType.ER, LocationType.MMR]
                    )
                )
            ) or 0,
            "racks": self.session.scalar(select(func.count(Rack.id))) or 0,
            "devices": self.session.scalar(select(func.count(Device.id))) or 0,
            "active_cables": self.session.scalar(
                select(func.count(Cable.id)).where(Cable.installation_status != CableStatus.REMOVED)
            ) or 0,
            "open_work_orders": self.session.scalar(
                select(func.count(WorkOrder.id)).where(
                    WorkOrder.status.not_in([WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED])
                )
            ) or 0,
            "failed_tests": self.session.scalar(
                select(func.count(TestRecord.id)).where(TestRecord.result == "FAIL")
            ) or 0,
            "expiring_access": self.session.scalar(
                select(func.count(AccessGrant.id)).where(
                    AccessGrant.status == AccessGrantStatus.ACTIVE
                )
            ) or 0,
        }
        recent = self.session.scalars(
            select(WorkOrder).order_by(WorkOrder.created_at.desc()).limit(5)
        ).all()
        return {
            "counts": counts,
            "recent_work_orders": [
                {
                    "id": str(item.id),
                    "number": item.work_order_number,
                    "title": item.title,
                    "status": item.status.value,
                    "due_at": item.due_at.isoformat() if item.due_at else None,
                }
                for item in recent
            ],
        }

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        require_permission(self.principal, "search:read")
        normalized = query.strip()
        if not normalized:
            return []
        like = f"%{normalized}%"
        results: list[dict[str, Any]] = []
        sources = [
            ("location", Location, Location.identifier, Location.name),
            ("rack", Rack, Rack.rack_identifier, Rack.name),
            ("device", Device, Device.identifier, Device.name),
            ("cable", Cable, Cable.identifier, Cable.identifier),
            ("work_order", WorkOrder, WorkOrder.work_order_number, WorkOrder.title),
        ]
        for resource_type, model, identifier_column, name_column in sources:
            rows = self.session.scalars(
                select(model)
                .where(or_(identifier_column.ilike(like), name_column.ilike(like)))
                .limit(limit)
            ).all()
            for row in rows:
                identifier = getattr(row, identifier_column.key)
                name = getattr(row, name_column.key)
                results.append(
                    {
                        "type": resource_type,
                        "id": str(row.id),
                        "identifier": identifier,
                        "name": name,
                        "exact": identifier.lower() == normalized.lower(),
                    }
                )
        results.sort(key=lambda item: (not item["exact"], item["type"], item["identifier"]))
        return results[:limit]
