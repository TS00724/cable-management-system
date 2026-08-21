from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class RolePreconditions:
    current_user: str
    superuser: bool
    bypassrls: bool
    table_owner: bool
    rls_enabled: bool
    rls_forced: bool


def assert_application_role_preconditions(values: Mapping[str, Any]) -> RolePreconditions:
    result = RolePreconditions(
        current_user=str(values["current_user"]),
        superuser=bool(values["superuser"]),
        bypassrls=bool(values["bypassrls"]),
        table_owner=bool(values["table_owner"]),
        rls_enabled=bool(values["rls_enabled"]),
        rls_forced=bool(values["rls_forced"]),
    )
    failures: list[str] = []
    if result.superuser:
        failures.append("application role is a superuser")
    if result.bypassrls:
        failures.append("application role has BYPASSRLS")
    if result.table_owner:
        failures.append("application role owns the protected table")
    if not result.rls_enabled:
        failures.append("RLS is not enabled on locations")
    if not result.rls_forced:
        failures.append("FORCE ROW LEVEL SECURITY is not enabled on locations")
    if failures:
        raise RuntimeError("Invalid RLS proof role: " + "; ".join(failures))
    return result


def _role_preconditions(connection) -> RolePreconditions:  # type: ignore[no-untyped-def]
    row = connection.execute(
        """
        SELECT
          current_user,
          role.rolsuper AS superuser,
          role.rolbypassrls AS bypassrls,
          relation.relowner = role.oid AS table_owner,
          relation.relrowsecurity AS rls_enabled,
          relation.relforcerowsecurity AS rls_forced
        FROM pg_roles AS role
        JOIN pg_class AS relation ON relation.oid = 'public.locations'::regclass
        WHERE role.rolname = current_user
        """
    ).fetchone()
    if row is None:
        raise RuntimeError("Unable to inspect PostgreSQL application role")
    return assert_application_role_preconditions(
        {
            "current_user": row[0],
            "superuser": row[1],
            "bypassrls": row[2],
            "table_owner": row[3],
            "rls_enabled": row[4],
            "rls_forced": row[5],
        }
    )


def run_matrix(application_dsn: str, platform_dsn: str) -> dict[str, Any]:
    try:
        import psycopg
        from psycopg import errors
    except ImportError as exc:  # pragma: no cover - depends on runtime packaging
        raise RuntimeError("psycopg is required for the PostgreSQL RLS matrix") from exc

    suffix = uuid.uuid4().hex[:10]
    organization_a, organization_b = uuid.uuid4(), uuid.uuid4()
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    location_a, location_b, own_insert = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    now = datetime.now(UTC)
    checks: dict[str, Any] = {}

    with psycopg.connect(platform_dsn, autocommit=True) as platform:
        try:
            platform.execute(
                """
                INSERT INTO organizations
                  (id, name, organization_type, external_reference, created_at, updated_at)
                VALUES
                  (%s, %s, 'CUSTOMER', NULL, %s, %s),
                  (%s, %s, 'CUSTOMER', NULL, %s, %s)
                """,
                (
                    organization_a,
                    f"RLS Tenant A {suffix}",
                    now,
                    now,
                    organization_b,
                    f"RLS Tenant B {suffix}",
                    now,
                    now,
                ),
            )
            platform.execute(
                """
                INSERT INTO tenants
                  (id, owner_organization_id, name, slug, compliance_mode,
                   active_standard_profile_id, active, created_at, updated_at)
                VALUES
                  (%s, %s, %s, %s, 'assisted', NULL, TRUE, %s, %s),
                  (%s, %s, %s, %s, 'assisted', NULL, TRUE, %s, %s)
                """,
                (
                    tenant_a,
                    organization_a,
                    f"RLS Tenant A {suffix}",
                    f"rls-a-{suffix}",
                    now,
                    now,
                    tenant_b,
                    organization_b,
                    f"RLS Tenant B {suffix}",
                    f"rls-b-{suffix}",
                    now,
                    now,
                ),
            )
            platform.execute(
                """
                INSERT INTO locations
                  (id, tenant_id, parent_id, location_type, identifier, name, status,
                   coordinates, dimensions, transform_3d, floor_plan_reference,
                   version, deleted_at, created_at, updated_at)
                VALUES
                  (%s, %s, NULL, 'CAMPUS', %s, 'Tenant A Campus', 'active',
                   '{}'::json, '{}'::json, '{}'::json, NULL, 1, NULL, %s, %s),
                  (%s, %s, NULL, 'CAMPUS', %s, 'Tenant B Campus', 'active',
                   '{}'::json, '{}'::json, '{}'::json, NULL, 1, NULL, %s, %s)
                """,
                (
                    location_a,
                    tenant_a,
                    f"RLS-A-{suffix}",
                    now,
                    now,
                    location_b,
                    tenant_b,
                    f"RLS-B-{suffix}",
                    now,
                    now,
                ),
            )

            with psycopg.connect(application_dsn, autocommit=True) as application:
                role = _role_preconditions(application)
                checks["role"] = asdict(role)
                application.execute(
                    "SELECT set_config('app.current_tenant', %s, false)", (str(tenant_a),)
                )

                listed = application.execute(
                    "SELECT tenant_id, identifier FROM locations ORDER BY identifier"
                ).fetchall()
                checks["list_hides_tenant_b"] = all(row[0] == tenant_a for row in listed)
                checks["list_contains_tenant_a"] = any(row[0] == tenant_a for row in listed)
                direct = application.execute(
                    "SELECT count(*) FROM locations WHERE id = %s", (location_b,)
                ).fetchone()[0]
                checks["direct_lookup_tenant_b_zero"] = direct == 0
                updated = application.execute(
                    "UPDATE locations SET name = 'ATTACK' WHERE id = %s", (location_b,)
                ).rowcount
                checks["update_tenant_b_zero"] = updated == 0
                deleted = application.execute(
                    "DELETE FROM locations WHERE id = %s", (location_b,)
                ).rowcount
                checks["delete_tenant_b_zero"] = deleted == 0

                cross_tenant_insert_rejected = False
                try:
                    application.execute(
                        """
                        INSERT INTO locations
                          (id, tenant_id, parent_id, location_type, identifier, name, status,
                           coordinates, dimensions, transform_3d, floor_plan_reference,
                           version, deleted_at, created_at, updated_at)
                        VALUES
                          (%s, %s, NULL, 'CAMPUS', %s, 'Attack', 'active',
                           '{}'::json, '{}'::json, '{}'::json, NULL, 1, NULL, %s, %s)
                        """,
                        (uuid.uuid4(), tenant_b, f"RLS-ATTACK-{suffix}", now, now),
                    )
                except errors.InsufficientPrivilege:
                    cross_tenant_insert_rejected = True
                checks["insert_tenant_b_rejected"] = cross_tenant_insert_rejected

                application.execute(
                    """
                    INSERT INTO locations
                      (id, tenant_id, parent_id, location_type, identifier, name, status,
                       coordinates, dimensions, transform_3d, floor_plan_reference,
                       version, deleted_at, created_at, updated_at)
                    VALUES
                      (%s, %s, NULL, 'CAMPUS', %s, 'Own Insert', 'active',
                       '{}'::json, '{}'::json, '{}'::json, NULL, 1, NULL, %s, %s)
                    """,
                    (own_insert, tenant_a, f"RLS-OWN-{suffix}", now, now),
                )
                own = application.execute(
                    "SELECT count(*) FROM locations WHERE id = %s", (own_insert,)
                ).fetchone()[0]
                checks["insert_tenant_a_succeeds"] = own == 1

            failed = [key for key, value in checks.items() if key != "role" and value is not True]
            if failed:
                raise AssertionError("PostgreSQL RLS matrix failed: " + ", ".join(failed))
            return {"status": "PASS", "tenant_a": str(tenant_a), "checks": checks}
        finally:
            platform.execute("DELETE FROM locations WHERE tenant_id IN (%s, %s)", (tenant_a, tenant_b))
            platform.execute("DELETE FROM tenants WHERE id IN (%s, %s)", (tenant_a, tenant_b))
            platform.execute(
                "DELETE FROM organizations WHERE id IN (%s, %s)",
                (organization_a, organization_b),
            )


def main() -> int:
    application_dsn = os.environ.get("RLS_TEST_APPLICATION_DSN")
    platform_dsn = os.environ.get("RLS_TEST_PLATFORM_DSN")
    if not application_dsn or not platform_dsn:
        print(
            json.dumps(
                {
                    "status": "NOT_EXECUTED",
                    "reason": "RLS_TEST_APPLICATION_DSN and RLS_TEST_PLATFORM_DSN are required",
                }
            )
        )
        return 2
    try:
        print(json.dumps(run_matrix(application_dsn, platform_dsn), default=str, sort_keys=True))
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
