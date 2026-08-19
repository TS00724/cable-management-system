from __future__ import annotations

import importlib.util
from pathlib import Path

from app.models import AuditEvent, Base, TenantOwnedMixin


def load_migration():
    path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "200000000002_postgresql_rls_and_audit_guard.py"
    )
    spec = importlib.util.spec_from_file_location("rls_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


def test_postgresql_rls_covers_every_tenant_table() -> None:
    module, _ = load_migration()
    model_tables = {
        mapper.local_table.name
        for mapper in Base.registry.mappers
        if issubclass(mapper.class_, TenantOwnedMixin)
    }
    model_tables.add(AuditEvent.__tablename__)
    assert set(module.TENANT_TABLES) == model_tables


def test_postgresql_rls_forces_policy_and_audit_trigger() -> None:
    _, path = load_migration()
    source = path.read_text()
    assert "FORCE ROW LEVEL SECURITY" in source
    assert "CREATE TRIGGER audit_events_append_only" in source
    assert "current_setting('app.current_tenant'" in source
