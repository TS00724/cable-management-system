"""Fiber splice topology. All links include tenant_id, including parent links.

A cassette slot is a numbered splice-tray position, not a chassis module bay.
Endpoint claims describe active occupancy; released splice records retain history.
"""
from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Float, ForeignKeyConstraint, Index, Integer
from sqlalchemy import String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, Cable, Device, Project, TenantOwnedMixin


# Referenced composite keys must exist both in metadata.create_all and migration 004.
for _parent in (Cable, Device, Project):
    Index(f"uq_{_parent.__tablename__}_fiber_tenant_id",
          _parent.__table__.c.tenant_id, _parent.__table__.c.id, unique=True)


def tenant_key(name: str):
    return UniqueConstraint("tenant_id", "id", name=f"uq_{name}_tenant_id")


def tenant_fk(column: str, parent: str):
    return ForeignKeyConstraint(
        ["tenant_id", column], [f"{parent}.tenant_id", f"{parent}.id"],
        ondelete="RESTRICT",
    )


class FiberBundle(Base, TenantOwnedMixin):
    __tablename__ = "fiber_bundles"
    __table_args__ = (
        tenant_key("fiber_bundles"), tenant_fk("cable_id", "cables"),
        UniqueConstraint("tenant_id", "cable_id", name="uq_fiber_bundle_cable"),
        CheckConstraint("strand_count BETWEEN 1 AND 576", name="ck_fiber_bundle_count"),
    )
    cable_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    strand_count: Mapped[int] = mapped_column(Integer, nullable=False)


class FiberStrand(Base, TenantOwnedMixin):
    __tablename__ = "fiber_strands"
    __table_args__ = (
        tenant_key("fiber_strands"), tenant_fk("bundle_id", "fiber_bundles"),
        UniqueConstraint("tenant_id", "bundle_id", "number", name="uq_fiber_strand_number"),
        CheckConstraint("number BETWEEN 1 AND 576", name="ck_fiber_strand_number"),
    )
    bundle_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)


class FiberCassette(Base, TenantOwnedMixin):
    __tablename__ = "fiber_cassettes"
    __table_args__ = (
        tenant_key("fiber_cassettes"), tenant_fk("device_id", "devices"),
        tenant_fk("project_id", "projects"),
        UniqueConstraint("tenant_id", "device_id", "name", name="uq_fiber_cassette_name"),
        CheckConstraint("slot_count BETWEEN 1 AND 288", name="ck_fiber_cassette_count"),
    )
    device_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slot_count: Mapped[int] = mapped_column(Integer, nullable=False)


class FiberCassetteSlot(Base, TenantOwnedMixin):
    __tablename__ = "fiber_cassette_slots"
    __table_args__ = (
        tenant_key("fiber_cassette_slots"), tenant_fk("cassette_id", "fiber_cassettes"),
        UniqueConstraint("tenant_id", "cassette_id", "number", name="uq_fiber_slot_number"),
        CheckConstraint("number BETWEEN 1 AND 288", name="ck_fiber_slot_number"),
    )
    cassette_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)


class FiberSplice(Base, TenantOwnedMixin):
    __tablename__ = "fiber_splices"
    __table_args__ = (
        tenant_key("fiber_splices"), tenant_fk("slot_id", "fiber_cassette_slots"),
        CheckConstraint("loss_db >= 0 AND loss_db <= 10", name="ck_fiber_splice_loss"),
        Index("uq_fiber_active_splice_slot", "tenant_id", "slot_id", unique=True,
              sqlite_where=text("deleted_at IS NULL"),
              postgresql_where=text("deleted_at IS NULL")),
    )
    slot_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    loss_db: Mapped[float] = mapped_column(Float, nullable=False)


class FiberSpliceEnd(Base, TenantOwnedMixin):
    __tablename__ = "fiber_splice_ends"
    __table_args__ = (
        tenant_key("fiber_splice_ends"), tenant_fk("splice_id", "fiber_splices"),
        tenant_fk("strand_id", "fiber_strands"),
        UniqueConstraint("tenant_id", "strand_id", "side", name="uq_fiber_endpoint_claim"),
        UniqueConstraint("tenant_id", "splice_id", "end_number", name="uq_fiber_splice_end"),
        CheckConstraint("side IN ('A', 'B')", name="ck_fiber_endpoint_side"),
        CheckConstraint("end_number IN (1, 2)", name="ck_fiber_splice_end_number"),
    )
    splice_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    strand_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    side: Mapped[str] = mapped_column(String(1), nullable=False)
    end_number: Mapped[int] = mapped_column(Integer, nullable=False)


FIBER_TABLES = (
    "fiber_bundles", "fiber_strands", "fiber_cassettes", "fiber_cassette_slots",
    "fiber_splices", "fiber_splice_ends",
)
