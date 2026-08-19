from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.audit import record_audit
from app.db import PlatformSessionLocal, create_all, platform_engine, set_platform_bypass
from app.models import (
    AccessGrant,
    AccessGrantStatus,
    Cable,
    CableStatus,
    Device,
    DeviceTemplate,
    Label,
    Location,
    LocationType,
    Organization,
    OrganizationType,
    Pathway,
    PathwaySegment,
    Port,
    Project,
    Rack,
    StandardProfile,
    Tenant,
    TenantMembership,
    UserIdentity,
    WorkOrder,
    WorkOrderStatus,
)
from app.security import resolve_principal
from app.services.connectivity import ConnectivityService
from app.services.infrastructure import InfrastructureService
from app.services.labels import LabelService

TENANT_SLUG = "northstar-university"


def admin_permissions() -> list[str]:
    return ["*"]


def supervisor_permissions() -> list[str]:
    return [
        "location:read",
        "rack:read",
        "device:read",
        "port:read",
        "pathway:read",
        "cable:read",
        "cable:trace",
        "cable:approve",
        "work_order:read",
        "compliance:read",
        "audit:read",
        "dashboard:read",
        "search:read",
        "label:create",
    ]


def contractor_permissions() -> list[str]:
    return [
        "location:read",
        "rack:read",
        "device:read",
        "port:read",
        "pathway:read",
        "cable:read",
        "cable:trace",
        "cable:install",
        "cable:test",
        "work_order:read",
        "label:create",
    ]


def ensure_standard_profile(session) -> StandardProfile:  # type: ignore[no-untyped-def]
    profile = session.scalar(
        select(StandardProfile).where(
            StandardProfile.tenant_id.is_(None),
            StandardProfile.standard_family == "TIA-606",
            StandardProfile.edition == "D",
        )
    )
    if profile:
        return profile
    profile = StandardProfile(
        name="TIA-606-D Configurable Baseline",
        standard_family="TIA-606",
        edition="D",
        effective_date=datetime(2021, 1, 1, tzinfo=UTC),
        status="active",
        rules_json={
            "identifier_regex": r"^[A-Z0-9][A-Z0-9-]{2,179}$",
            "compliance_modes": ["strict", "assisted", "custom"],
            "notice": "Policy scaffolding only; exact proprietary clauses require a licensed source.",
        },
        identifier_templates={
            "location": "{parent}-{code}",
            "rack": "{campus}-{building}-{floor}-{space}-R{sequence:02d}",
            "device": "{campus}-{building}-{floor}-{space}-{kind}{sequence:02d}",
            "cable": "{campus}-{building}-{floor}-{space}-{kind}-{sequence:05d}",
        },
        validation_rules=[
            {"id": "generic-identifier-format", "type": "regex", "severity": "warning", "clause": None}
        ],
        label_templates={
            "cable-default": {
                "human_readable": "{identifier}",
                "barcode": "qr",
                "dimensions_mm": [50, 25],
            }
        },
        required_records={
            "cable": ["identifier", "media_type", "termination_a", "termination_b"],
            "rack": ["identifier", "location", "height_u"],
        },
    )
    session.add(profile)
    session.flush()
    return profile


def seed() -> dict[str, str]:
    create_all(platform_engine)
    with PlatformSessionLocal() as session:
        set_platform_bypass(session)
        existing = session.scalar(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        if existing:
            owner = session.scalar(
                select(UserIdentity).where(UserIdentity.email == "alice.admin@northstar.example")
            )
            supervisor = session.scalar(
                select(UserIdentity).where(UserIdentity.email == "sam.supervisor@northstar.example")
            )
            contractor = session.scalar(
                select(UserIdentity).where(UserIdentity.email == "tina.tech@metro.example")
            )
            rack = session.scalar(
                select(Rack).where(
                    Rack.tenant_id == existing.id,
                    Rack.rack_identifier == "MC-ENG-F02-TR02-R01",
                )
            )
            cable = session.scalar(
                select(Cable).where(
                    Cable.tenant_id == existing.id,
                    Cable.identifier == "MC-ENG-F02-TR02-HC-00001",
                )
            )
            work_order = session.scalar(
                select(WorkOrder).where(
                    WorkOrder.tenant_id == existing.id,
                    WorkOrder.work_order_number == "WO-ENG-0001",
                )
            )
            project = session.scalar(
                select(Project).where(
                    Project.tenant_id == existing.id,
                    Project.project_number == "ENG-UPG-2026",
                )
            )
            tr = session.scalar(
                select(Location).where(
                    Location.tenant_id == existing.id,
                    Location.identifier == "MC-ENG-F02-TR02",
                )
            )
            return {
                "tenant_id": str(existing.id),
                "owner_id": str(owner.id) if owner else "",
                "supervisor_id": str(supervisor.id) if supervisor else "",
                "contractor_id": str(contractor.id) if contractor else "",
                "project_id": str(project.id) if project else "",
                "location_id": str(tr.id) if tr else "",
                "rack_id": str(rack.id) if rack else "",
                "cable_id": str(cable.id) if cable else "",
                "work_order_id": str(work_order.id) if work_order else "",
            }

        profile = ensure_standard_profile(session)
        customer_org = Organization(
            name="Northstar University", organization_type=OrganizationType.CUSTOMER
        )
        contractor_org = Organization(
            name="Metro Structured Cabling Ltd",
            organization_type=OrganizationType.CONTRACTOR,
        )
        other_org = Organization(
            name="Contoso Data Services", organization_type=OrganizationType.CUSTOMER
        )
        session.add_all([customer_org, contractor_org, other_org])
        session.flush()

        owner = UserIdentity(
            organization_id=customer_org.id,
            email="alice.admin@northstar.example",
            display_name="Alice Admin",
        )
        supervisor = UserIdentity(
            organization_id=customer_org.id,
            email="sam.supervisor@northstar.example",
            display_name="Sam Supervisor",
        )
        contractor = UserIdentity(
            organization_id=contractor_org.id,
            email="tina.tech@metro.example",
            display_name="Tina Technician",
        )
        other_owner = UserIdentity(
            organization_id=other_org.id,
            email="owner@contoso.example",
            display_name="Contoso Owner",
        )
        session.add_all([owner, supervisor, contractor, other_owner])
        session.flush()

        tenant = Tenant(
            owner_organization_id=customer_org.id,
            name="Northstar University",
            slug=TENANT_SLUG,
            active_standard_profile_id=profile.id,
            compliance_mode="assisted",
        )
        other_tenant = Tenant(
            owner_organization_id=other_org.id,
            name="Contoso Data Services",
            slug="contoso-data-services",
            active_standard_profile_id=profile.id,
        )
        session.add_all([tenant, other_tenant])
        session.flush()
        session.add_all(
            [
                TenantMembership(
                    tenant_id=tenant.id,
                    user_id=owner.id,
                    role="Tenant Owner",
                    permissions=admin_permissions(),
                ),
                TenantMembership(
                    tenant_id=tenant.id,
                    user_id=supervisor.id,
                    role="Infrastructure Manager",
                    permissions=supervisor_permissions(),
                ),
                TenantMembership(
                    tenant_id=other_tenant.id,
                    user_id=other_owner.id,
                    role="Tenant Owner",
                    permissions=admin_permissions(),
                ),
            ]
        )
        session.commit()

        admin = resolve_principal(session, actor_id=owner.id, tenant_id=tenant.id)
        infrastructure = InfrastructureService(session, admin)
        campus = infrastructure.create_location(
            location_type=LocationType.CAMPUS, identifier="MC", name="Main Campus"
        )
        admin_bldg = infrastructure.create_location(
            location_type=LocationType.BUILDING,
            identifier="MC-ADM",
            name="Administration Building",
            parent_id=campus.id,
        )
        engineering = infrastructure.create_location(
            location_type=LocationType.BUILDING,
            identifier="MC-ENG",
            name="Engineering Building",
            parent_id=campus.id,
        )
        dc1 = infrastructure.create_location(
            location_type=LocationType.BUILDING,
            identifier="MC-DC1",
            name="Data Center 1",
            parent_id=campus.id,
        )
        eng_floor = infrastructure.create_location(
            location_type=LocationType.FLOOR,
            identifier="MC-ENG-F02",
            name="Floor 2",
            parent_id=engineering.id,
            dimensions={"width_m": 80, "depth_m": 40, "height_m": 3.2},
        )
        tr = infrastructure.create_location(
            location_type=LocationType.TR,
            identifier="MC-ENG-F02-TR02",
            name="TR-02",
            parent_id=eng_floor.id,
            dimensions={"width_m": 6, "depth_m": 4, "height_m": 3.2},
            coordinates={"x": 28, "y": 10},
        )
        for number in (1, 3):
            infrastructure.create_location(
                location_type=LocationType.TR,
                identifier=f"MC-ENG-TR{number:02d}",
                name=f"TR-{number:02d}",
                parent_id=engineering.id,
            )
        eng_mdf = infrastructure.create_location(
            location_type=LocationType.MDF,
            identifier="MC-ENG-MDF",
            name="Engineering MDF",
            parent_id=engineering.id,
        )
        dc_floor = infrastructure.create_location(
            location_type=LocationType.FLOOR,
            identifier="MC-DC1-F01",
            name="Floor 1",
            parent_id=dc1.id,
        )
        data_hall = infrastructure.create_location(
            location_type=LocationType.DATA_HALL,
            identifier="MC-DC1-F01-DHA",
            name="Data Hall A",
            parent_id=dc_floor.id,
        )
        rows: dict[str, Location] = {}
        for row_name in ("A", "B"):
            rows[row_name] = infrastructure.create_location(
                location_type=LocationType.ROW,
                identifier=f"MC-DC1-F01-DHA-ROW{row_name}",
                name=f"Row {row_name}",
                parent_id=data_hall.id,
            )
        infrastructure.create_location(
            location_type=LocationType.MMR,
            identifier="MC-DC1-F01-MMR",
            name="MMR",
            parent_id=dc_floor.id,
        )
        dc_mdf = infrastructure.create_location(
            location_type=LocationType.MDF,
            identifier="MC-DC1-F01-MDF",
            name="MDF",
            parent_id=dc_floor.id,
        )

        project = Project(
            tenant_id=tenant.id,
            project_number="ENG-UPG-2026",
            name="Engineering Building Upgrade Project",
            customer_organization_id=customer_org.id,
            contractor_organization_id=contractor_org.id,
            status="active",
            planned_start=datetime.now(UTC) - timedelta(days=7),
            planned_end=datetime.now(UTC) + timedelta(days=60),
        )
        session.add(project)
        session.flush()
        record_audit(
            session,
            principal=admin,
            action="project.created",
            object_type="project",
            object_id=project.id,
            after={"project_number": project.project_number, "name": project.name},
            project_id=project.id,
        )
        grant = AccessGrant(
            tenant_id=tenant.id,
            subject_organization_id=contractor_org.id,
            subject_user_id=contractor.id,
            project_id=project.id,
            location_id=engineering.id,
            permissions=contractor_permissions(),
            approved_by=owner.id,
            starts_at=datetime.now(UTC) - timedelta(days=1),
            expires_at=datetime.now(UTC) + timedelta(days=90),
            status=AccessGrantStatus.ACTIVE,
        )
        session.add(grant)
        session.flush()
        record_audit(
            session,
            principal=admin,
            action="accessgrant.created",
            object_type="access_grant",
            object_id=grant.id,
            after={"subject": str(contractor.id), "project": str(project.id)},
            project_id=project.id,
        )

        patch_template = infrastructure.create_template(
            manufacturer="SIM Reference",
            model="PP-48-CAT6A",
            device_type="patch_panel",
            rack_units=1,
            depth_mm=120,
            port_blueprint=[
                {
                    "count": 48,
                    "prefix": "F",
                    "face": "front",
                    "connector_type": "RJ45",
                    "media_type": "copper",
                    "mapping_key": "channel",
                },
                {
                    "count": 48,
                    "prefix": "R",
                    "face": "rear",
                    "connector_type": "punchdown",
                    "media_type": "copper",
                    "termination_type": "110-block",
                    "mapping_key": "channel",
                },
            ],
        )
        switch_template = infrastructure.create_template(
            manufacturer="SIM Reference",
            model="ACCESS-48",
            device_type="switch",
            rack_units=1,
            port_blueprint=[
                {
                    "count": 48,
                    "prefix": "G",
                    "face": "front",
                    "connector_type": "RJ45",
                    "media_type": "copper",
                }
            ],
        )
        fiber_template = infrastructure.create_template(
            manufacturer="SIM Reference",
            model="FIBER-12-LC",
            device_type="fiber_patch_panel",
            rack_units=1,
            depth_mm=150,
            port_blueprint=[
                {
                    "count": 12,
                    "prefix": "F",
                    "face": "front",
                    "connector_type": "LC",
                    "media_type": "fiber",
                    "mapping_key": "fiber",
                },
                {
                    "count": 12,
                    "prefix": "R",
                    "face": "rear",
                    "connector_type": "LC",
                    "media_type": "fiber",
                    "mapping_key": "fiber",
                },
            ],
        )

        rack = infrastructure.create_rack(
            location_id=tr.id,
            rack_identifier="MC-ENG-F02-TR02-R01",
            name="Rack TR02-R01",
            height_u=42,
            position_x=1.5,
            position_y=1.0,
            reserved_units=[39],
        )
        panel = infrastructure.create_device_from_template(
            rack_id=rack.id,
            template_id=patch_template.id,
            identifier="MC-ENG-F02-TR02-PP01",
            name="48-port Cat6A Patch Panel",
            start_u=40,
        )
        switch = infrastructure.create_device_from_template(
            rack_id=rack.id,
            template_id=switch_template.id,
            identifier="MC-ENG-F02-TR02-SW01",
            name="48-port Access Switch",
            start_u=38,
        )
        eng_mdf_rack = infrastructure.create_rack(
            location_id=eng_mdf.id,
            rack_identifier="MC-ENG-MDF-R01",
            name="Engineering MDF Rack",
            height_u=42,
        )
        dc_mdf_rack = infrastructure.create_rack(
            location_id=dc_mdf.id,
            rack_identifier="MC-DC1-F01-MDF-R01",
            name="Data Center MDF Rack",
            height_u=48,
        )
        eng_fiber_panel = infrastructure.create_device_from_template(
            rack_id=eng_mdf_rack.id,
            template_id=fiber_template.id,
            identifier="MC-ENG-MDF-FPP01",
            name="Engineering OS2 Fiber Panel",
            start_u=40,
        )
        dc_fiber_panel = infrastructure.create_device_from_template(
            rack_id=dc_mdf_rack.id,
            template_id=fiber_template.id,
            identifier="MC-DC1-F01-MDF-FPP01",
            name="Data Center OS2 Fiber Panel",
            start_u=46,
        )
        for row_name, count in (("A", 3), ("B", 2)):
            for number in range(1, count + 1):
                infrastructure.create_rack(
                    location_id=rows[row_name].id,
                    rack_identifier=f"MC-DC1-F01-DHA-{row_name}{number:02d}",
                    name=f"Data Hall A Rack {row_name}{number:02d}",
                    height_u=48,
                    position_x=number * 1.2,
                    position_y=0 if row_name == "A" else 2.0,
                )

        outlet = Device(
            tenant_id=tenant.id,
            location_id=eng_floor.id,
            identifier="MC-ENG-F02-WA-2-101-A",
            name="WA-2-101-A",
            device_type="outlet",
            rack_units=1,
            start_u=1,
            face="front",
        )
        session.add(outlet)
        session.flush()
        outlet_port = Port(
            tenant_id=tenant.id,
            device_id=outlet.id,
            identifier="A",
            label="A",
            connector_type="RJ45",
            media_type="copper",
            front_or_rear="front",
            position_index=1,
        )
        session.add(outlet_port)
        session.flush()

        pathway = Pathway(
            tenant_id=tenant.id,
            location_id=eng_floor.id,
            identifier="MC-ENG-F02-TRAY-01",
            name="Engineering Floor 2 Cable Tray",
            pathway_type="basket_tray",
            capacity_area_mm2=120000,
        )
        session.add(pathway)
        session.flush()
        segments: list[PathwaySegment] = []
        for sequence, name, length, coordinates in [
            (1, "TR-02 Tray", 4.0, [{"x": 1.0, "y": 2.8, "z": 2.7}, {"x": 5.0, "y": 2.8, "z": 2.7}]),
            (2, "Main Corridor Tray", 34.0, [{"x": 5.0, "y": 2.8, "z": 2.7}, {"x": 39.0, "y": 2.8, "z": 2.7}]),
            (3, "Zone Drop WA-2-101", 8.0, [{"x": 39.0, "y": 2.8, "z": 2.7}, {"x": 42.0, "y": 8.0, "z": 0.5}]),
        ]:
            segment = PathwaySegment(
                tenant_id=tenant.id,
                pathway_id=pathway.id,
                sequence=sequence,
                name=name,
                length_m=length,
                capacity_area_mm2=40000,
                reserved_percent=10,
                coordinates=coordinates,
            )
            session.add(segment)
            segments.append(segment)
        session.flush()
        backbone_pathway = Pathway(
            tenant_id=tenant.id,
            location_id=campus.id,
            identifier="MC-BB-DUCT-01",
            name="Campus Backbone Duct Bank",
            pathway_type="duct_bank",
            capacity_area_mm2=300000,
        )
        session.add(backbone_pathway)
        session.flush()
        backbone_segment = PathwaySegment(
            tenant_id=tenant.id,
            pathway_id=backbone_pathway.id,
            sequence=1,
            name="Engineering to Data Center 1",
            length_m=420,
            capacity_area_mm2=150000,
            reserved_percent=25,
            coordinates=[{"x": 0, "y": 0, "z": -1}, {"x": 420, "y": 30, "z": -1}],
        )
        session.add(backbone_segment)
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
        eng_fiber_rear = session.scalar(
            select(Port).where(Port.device_id == eng_fiber_panel.id, Port.identifier == "R01")
        )
        dc_fiber_rear = session.scalar(
            select(Port).where(Port.device_id == dc_fiber_panel.id, Port.identifier == "R01")
        )
        assert switch_port and panel_front and panel_rear and eng_fiber_rear and dc_fiber_rear

        connectivity = ConnectivityService(session, admin)
        patch = connectivity.create_cable(
            identifier="MC-ENG-F02-TR02-PC-00001",
            media_type="Cat6A copper",
            construction="patch_cord",
            port_a_id=switch_port.id,
            port_b_id=panel_front.id,
            project_id=project.id,
            color="blue",
            length_m=2.0,
        )
        horizontal = connectivity.create_cable(
            identifier="MC-ENG-F02-TR02-HC-00001",
            media_type="Cat6A copper",
            construction="horizontal_cable",
            port_a_id=panel_rear.id,
            port_b_id=outlet_port.id,
            project_id=project.id,
            color="blue",
            length_m=46.0,
            route_segment_ids=[segment.id for segment in segments],
        )
        backbone = connectivity.create_cable(
            identifier="MC-BB-OS2-00001",
            media_type="OS2 fiber",
            construction="fiber_trunk",
            port_a_id=eng_fiber_rear.id,
            port_b_id=dc_fiber_rear.id,
            project_id=project.id,
            color="yellow",
            length_m=420,
            route_segment_ids=[backbone_segment.id],
        )
        patch.installation_status = CableStatus.STAGED
        horizontal.installation_status = CableStatus.STAGED
        backbone.strand_count = 12
        backbone.installation_status = CableStatus.IN_SERVICE
        backbone.test_status = "PASS"
        backbone.installed_at = datetime.now(UTC) - timedelta(days=180)
        backbone.tested_at = datetime.now(UTC) - timedelta(days=179)

        work_order = WorkOrder(
            tenant_id=tenant.id,
            project_id=project.id,
            location_id=tr.id,
            cable_id=horizontal.id,
            work_order_number="WO-ENG-0001",
            title="Install and certify WA-2-101-A horizontal link",
            description="Install Cat6A cable, terminate, test and submit as-built evidence.",
            assigned_organization_id=contractor_org.id,
            assigned_user_id=contractor.id,
            status=WorkOrderStatus.READY,
            due_at=datetime.now(UTC) + timedelta(days=14),
            created_by=owner.id,
        )
        session.add(work_order)
        session.flush()
        record_audit(
            session,
            principal=admin,
            action="workorder.created",
            object_type="work_order",
            object_id=work_order.id,
            after={"number": work_order.work_order_number, "assigned_to": str(contractor.id)},
            project_id=project.id,
        )
        LabelService(session, admin).create_cable_label(horizontal.id, "http://localhost:8000")

        private_location = Location(
            tenant_id=other_tenant.id,
            location_type=LocationType.DATA_HALL,
            identifier="CONTOSO-PRIVATE-DH1",
            name="Private Data Hall",
        )
        session.add(private_location)
        session.flush()
        private_rack = Rack(
            tenant_id=other_tenant.id,
            location_id=private_location.id,
            rack_identifier="CONTOSO-PRIVATE-R01",
            name="Contoso Private Rack",
            height_u=48,
        )
        session.add(private_rack)
        session.commit()
        return {
            "tenant_id": str(tenant.id),
            "owner_id": str(owner.id),
            "supervisor_id": str(supervisor.id),
            "contractor_id": str(contractor.id),
            "project_id": str(project.id),
            "location_id": str(tr.id),
            "rack_id": str(rack.id),
            "cable_id": str(horizontal.id),
            "work_order_id": str(work_order.id),
            "second_tenant_id": str(other_tenant.id),
            "private_rack_id": str(private_rack.id),
        }


if __name__ == "__main__":
    context = seed()
    print("Northstar demo seed ready")
    for key, value in context.items():
        print(f"{key}={value}")
