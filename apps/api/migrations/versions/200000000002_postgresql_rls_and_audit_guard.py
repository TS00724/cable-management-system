"""PostgreSQL tenant RLS and append-only audit guard.

Revision ID: 200000000002
Revises: 5959e77dbc77
"""
from collections.abc import Sequence

from alembic import op

revision: str = "200000000002"
down_revision: str | Sequence[str] | None = "5959e77dbc77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = [
    "tenant_memberships", "projects", "locations", "access_grants", "racks",
    "device_templates", "devices", "ports", "port_mappings", "pathways",
    "pathway_segments", "cables", "cable_terminations", "cable_route_segments",
    "work_orders", "test_records", "labels", "audit_events",
]


def _tenant_policy(table: str) -> str:
    return (
        f'CREATE POLICY tenant_isolation ON "{table}" '
        "USING (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid) "
        "WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid)"
    )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table in TENANT_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"')
        op.execute(_tenant_policy(table))
    op.execute('ALTER TABLE "tenants" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "tenants" FORCE ROW LEVEL SECURITY')
    op.execute('DROP POLICY IF EXISTS tenant_self ON "tenants"')
    op.execute(
        "CREATE POLICY tenant_self ON tenants "
        "USING (id = nullif(current_setting('app.current_tenant', true), '')::uuid) "
        "WITH CHECK (id = nullif(current_setting('app.current_tenant', true), '')::uuid)"
    )
    op.execute('ALTER TABLE "standard_profiles" ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "standard_profiles" FORCE ROW LEVEL SECURITY')
    op.execute('DROP POLICY IF EXISTS standard_profile_read ON "standard_profiles"')
    op.execute(
        "CREATE POLICY standard_profile_read ON standard_profiles FOR SELECT "
        "USING (tenant_id IS NULL OR tenant_id = "
        "nullif(current_setting('app.current_tenant', true), '')::uuid)"
    )
    op.execute('DROP POLICY IF EXISTS standard_profile_write ON "standard_profiles"')
    op.execute(
        "CREATE POLICY standard_profile_write ON standard_profiles FOR ALL "
        "USING (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid) "
        "WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant', true), '')::uuid)"
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION reject_audit_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'audit_events is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute('DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events')
    op.execute(
        'CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events '
        'FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation()'
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute('DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events')
    op.execute('DROP FUNCTION IF EXISTS reject_audit_mutation')
    op.execute('ALTER TABLE "standard_profiles" DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE "tenants" DISABLE ROW LEVEL SECURITY')
    for table in reversed(TENANT_TABLES):
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
