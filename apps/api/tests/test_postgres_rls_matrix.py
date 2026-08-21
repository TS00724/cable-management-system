from __future__ import annotations

import os

import pytest

from scripts.postgres_rls_attack_matrix import (
    assert_application_role_preconditions,
    run_matrix,
)


def test_application_role_preconditions_accept_non_owner_forced_rls_role() -> None:
    result = assert_application_role_preconditions(
        {
            "current_user": "sim_app",
            "superuser": False,
            "bypassrls": False,
            "table_owner": False,
            "rls_enabled": True,
            "rls_forced": True,
        }
    )
    assert result.current_user == "sim_app"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("superuser", True, "superuser"),
        ("bypassrls", True, "BYPASSRLS"),
        ("table_owner", True, "owns"),
        ("rls_enabled", False, "not enabled"),
        ("rls_forced", False, "FORCE"),
    ],
)
def test_application_role_preconditions_reject_invalid_proof_role(
    field: str, value: bool, message: str
) -> None:
    values = {
        "current_user": "sim_app",
        "superuser": False,
        "bypassrls": False,
        "table_owner": False,
        "rls_enabled": True,
        "rls_forced": True,
    }
    values[field] = value
    with pytest.raises(RuntimeError, match=message):
        assert_application_role_preconditions(values)


def test_real_postgresql_forced_rls_attack_matrix() -> None:
    application_dsn = os.environ.get("RLS_TEST_APPLICATION_DSN")
    platform_dsn = os.environ.get("RLS_TEST_PLATFORM_DSN")
    if not application_dsn or not platform_dsn:
        pytest.skip("real PostgreSQL RLS runtime DSNs are not configured")
    result = run_matrix(application_dsn, platform_dsn)
    assert result["status"] == "PASS"
