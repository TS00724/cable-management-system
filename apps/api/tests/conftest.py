from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import db as db_module  # noqa: F401
from app.models import (
    AccessGrant,
    AccessGrantStatus,
    Base,
    Device,
    DeviceTemplate,
    Location,
    LocationType,
    Organization,
    OrganizationType,
    Port,
    Project,
    Rack,
    StandardProfile,
    Tenant,
    TenantMembership,
    UserIdentity,
)
from app.security import resolve_principal
from app.services.connectivity import ConnectivityService
from app.services.infrastructure import InfrastructureService


@dataclass(frozen=True)
class World:
    session_factory: sessionmaker[Session]
    tenant_a: uuid.UUID
    tenant_b: uuid.UUID
    admin: uuid.UUID
    supervisor: uuid.UUID
    contractor: uuid.UUID
    contractor_org: uuid.UUID
    project: uuid.UUID
    campus: uuid.UUID
    building: uuid.UUID
    tr: uuid.UUID
    other_building: uuid.UUID
    rack: uuid.UUID
    private_rack: uuid.UUID
    switch: uuid.UUID
    panel: uuid.UUID
    outlet: uuid.UUID
    patch_cord: uuid.UUID
    horizontal_cable: uuid.UUID
    patch_template: uuid.UUID
    switch_template: uuid.UUID

    def scoped_session(self, tenant_id: uuid.UUID | None = None) -> Session:
        session = self.session_factory()
        session.info["tenant_id"] = tenant_id or self.tenant_a
        return session


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, class_=Session, autoflush=False, expire_on_commit=False)


@pytest.fixture
def world(session_factory: sessionmaker[Session]) -> World:
    with session_factory() as session:
        session.info["bypass_tenant"] = True
        profile = StandardProfile(
            name="Test TIA-606-D",
            standard_family="TIA-606",
            edition="D",
            status="active",
            rules_json={"identifier_regex": r"^[A-Z0-9][A-Z0-9-]{2,179}$"},
            identifier_templates={
                "location": "{parent}-{code}",
                "rack": "{campus}-{building}-{floor}-{space}-R{sequence:02d}",
                "device": "{campus}-{building}-{floor}-{space}-{kind}{sequence:02d}",
                "cable": "{campus}-{building}-{floor}-{space}-{kind}-{sequence:05d}",
            },
            validation_rules=[],
            label_templates={"cable-default": {}},
            required_records={},
        )
        customer_org = Organization(name="Tenant A", organization_type=OrganizationType.CUSTOMER)
        other_org = Organization(name="Tenant B", organization_type=OrganizationType.CUSTOMER)
        contractor_org = Organization(
            name="Scoped Contractor", organization_type=OrganizationType.CONTRACTOR
        )
        session.add_all([profile, customer_org, other_org, contractor_org])
        session.flush()
        admin = UserIdentity(
            organization_id=customer_org.id, email="admin@test.example", display_name="Admin"
        )
        supervisor = UserIdentity(
            organization_id=customer_org.id,
            email="supervisor@test.example",
            display_name="Supervisor",
        )
        contractor = UserIdentity(
            organization_id=contractor_org.id,
            email="contractor@test.example",
            display_name="Contractor",
        )
        other_owner = UserIdentity(
            organization_id=other_org.id, email="other@test.example", display_name="Other"
        )
        session.add_all([admin, supervisor, contractor, other_owner])
        session.flush()
        tenant_a = Tenant(
            owner_organization_id=customer_org.id,
            name="Tenant A",
            slug="tenant-a",
            active_standard_profile_id=profile.id,
        )
        tenant_b = Tenant(
            owner_organization_id=other_org.id,
            name="Tenant B",
            slug="tenant-b",
            active_standard_profile_id=profile.id,
        )
        session.add_all([tenant_a, tenant_b])
        session.flush()
        session.add_all(
            [
                TenantMembership(
                    tenant_id=tenant_a.id,
                    user_id=admin.id,
                    role="Tenant Owner",
                    permissions=["*"],
                ),
                TenantMembership(
                    tenant_id=tenant_a.id,
                    user_id=supervisor.id,
                    role="Infrastructure Manager",
                    permissions=[
                        "cable:read",
                        "cable:trace",
                        "cable:approve",
                        "rack:read",
                        "audit:read",
                        "dashboard:read",
                        "compliance:read",
                        "search:read",
                        "label:create",
                    ],
                ),
                TenantMembership(
                    tenant_id=tenant_b.id,
                    user_id=other_owner.id,
                    role="Tenant Owner",
                    permissions=["*"],
                ),
            ]
        )
        private_location = Location(
            tenant_id=tenant_b.id,
            location_type=LocationType.DATA_HALL,
            identifier="B-PRIVATE-DH",
            name="Private Hall",
        )
        session.add(private_location)
        session.flush()
        private_rack = Rack(
            tenant_id=tenant_b.id,
            location_id=private_location.id,
            rack_identifier="B-PRIVATE-R01",
            name="Private Rack",
            height_u=48,
        )
        session.add(private_rack)
        session.commit()

        session.info["bypass_tenant"] = False
        session.info["tenant_id"] = tenant_a.id
        principal = resolve_principal(session, actor_id=admin.id, tenant_id=tenant_a.id)
        infra = InfrastructureService(session, principal)
        campus = infra.create_location(
            location_type=LocationType.CAMPUS, identifier="A-MC", name="Main Campus"
        )
        building = infra.create_location(
            location_type=LocationType.BUILDING,
            identifier="A-MC-ENG",
            name="Engineering",
            parent_id=campus.id,
        )
        tr = infra.create_location(
            location_type=LocationType.TR,
            identifier="A-MC-ENG-TR01",
            name="TR-01",
            parent_id=building.id,
        )
        other_building = infra.create_location(
            location_type=LocationType.BUILDING,
            identifier="A-MC-ADM",
            name="Administration",
            parent_id=campus.id,
        )
        project = Project(
            tenant_id=tenant_a.id,
            project_number="P-100",
            name="Engineering Upgrade",
            customer_organization_id=customer_org.id,
            contractor_organization_id=contractor_org.id,
        )
        session.add(project)
        session.flush()
        session.add(
            AccessGrant(
                tenant_id=tenant_a.id,
                subject_user_id=contractor.id,
                subject_organization_id=contractor_org.id,
                project_id=project.id,
                location_id=building.id,
                permissions=[
                    "rack:read",
                    "device:read",
                    "port:read",
                    "cable:read",
                    "cable:trace",
                    "cable:install",
                    "cable:test",
                    "work_order:read",
                    "label:create",
                ],
                approved_by=admin.id,
                starts_at=datetime.now(UTC) - timedelta(hours=1),
                expires_at=datetime.now(UTC) + timedelta(days=1),
                status=AccessGrantStatus.ACTIVE,
            )
        )
        patch_template = infra.create_template(
            manufacturer="Test",
            model="PP-2",
            device_type="patch_panel",
            rack_units=1,
            port_blueprint=[
                {
                    "count": 2,
                    "prefix": "F",
                    "face": "front",
                    "connector_type": "RJ45",
                    "media_type": "copper",
                    "mapping_key": "channel",
                },
                {
                    "count": 2,
                    "prefix": "R",
                    "face": "rear",
                    "connector_type": "punchdown",
                    "media_type": "copper",
                    "mapping_key": "channel",
                },
            ],
        )
        switch_template = infra.create_template(
            manufacturer="Test",
            model="SW-2",
            device_type="switch",
            rack_units=1,
            port_blueprint=[
                {
                    "count": 2,
                    "prefix": "G",
                    "face": "front",
                    "connector_type": "RJ45",
                    "media_type": "copper",
                }
            ],
        )
        rack = infra.create_rack(
            location_id=tr.id,
            rack_identifier="A-MC-ENG-TR01-R01",
            name="Rack 1",
            height_u=42,
            reserved_units=[39],
        )
        panel = infra.create_device_from_template(
            rack_id=rack.id,
            template_id=patch_template.id,
            identifier="A-MC-ENG-TR01-PP01",
            name="Patch Panel",
            start_u=40,
        )
        switch = infra.create_device_from_template(
            rack_id=rack.id,
            template_id=switch_template.id,
            identifier="A-MC-ENG-TR01-SW01",
            name="Switch",
            start_u=38,
        )
        outlet = Device(
            tenant_id=tenant_a.id,
            location_id=building.id,
            identifier="A-MC-ENG-WA-001",
            name="WA-001",
            device_type="outlet",
            rack_units=1,
            start_u=1,
            face="front",
        )
        session.add(outlet)
        session.flush()
        outlet_port = Port(
            tenant_id=tenant_a.id,
            device_id=outlet.id,
            identifier="A",
            label="A",
            connector_type="RJ45",
            media_type="copper",
            position_index=1,
        )
        session.add(outlet_port)
        session.flush()
        switch_port = session.scalar(
            select(Port).where(Port.device_id == switch.id, Port.identifier == "G01")
        )
        panel_front = session.scalar(
            select(Port).where(Port.device_id == panel.id, Port.identifier == "F01")
        )
        panel_rear = session.scalar(
            select(Port).where(Port.device_id == panel.id, Port.identifier == "R01")
        )
        assert switch_port and panel_front and panel_rear
        connectivity = ConnectivityService(session, principal)
        patch_cord = connectivity.create_cable(
            identifier="A-MC-ENG-TR01-PC-00001",
            media_type="Cat6A copper",
            construction="patch_cord",
            port_a_id=switch_port.id,
            port_b_id=panel_front.id,
            project_id=project.id,
        )
        horizontal = connectivity.create_cable(
            identifier="A-MC-ENG-TR01-HC-00001",
            media_type="Cat6A copper",
            construction="horizontal_cable",
            port_a_id=panel_rear.id,
            port_b_id=outlet_port.id,
            project_id=project.id,
        )
        session.commit()
        return World(
            session_factory=session_factory,
            tenant_a=tenant_a.id,
            tenant_b=tenant_b.id,
            admin=admin.id,
            supervisor=supervisor.id,
            contractor=contractor.id,
            contractor_org=contractor_org.id,
            project=project.id,
            campus=campus.id,
            building=building.id,
            tr=tr.id,
            other_building=other_building.id,
            rack=rack.id,
            private_rack=private_rack.id,
            switch=switch.id,
            panel=panel.id,
            outlet=outlet.id,
            patch_cord=patch_cord.id,
            horizontal_cable=horizontal.id,
            patch_template=patch_template.id,
            switch_template=switch_template.id,
        )
