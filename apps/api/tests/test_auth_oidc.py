from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError

from app import auth
from app.api import deps
from app.auth import resolve_oidc_actor, verify_oidc_token
from app.config import Settings
from app.exceptions import AuthenticationError, AuthorizationError
from app.main import app
from app.models import UserIdentity


ISSUER = "https://identity.example/realms/sim"
AUDIENCE = "sim-api"
KEY_ID = "test-key"
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_JWK = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(PRIVATE_KEY.public_key()))
PUBLIC_JWK.update({"kid": KEY_ID, "alg": "RS256", "use": "sig"})


def oidc_settings(**overrides) -> Settings:  # type: ignore[no-untyped-def]
    values = {
        "app_env": "development",
        "auth_mode": "oidc",
        "demo_mode": False,
        "oidc_issuer_url": ISSUER,
        "oidc_audience": AUDIENCE,
        "oidc_jwks_json": json.dumps({"keys": [PUBLIC_JWK]}),
        "oidc_clock_skew_seconds": 0,
        "allowed_hosts": ["testserver"],
        "rate_limit_enabled": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def token_for(
    *,
    subject: str = "oidc-admin",
    tenant_id: str = "tenant",
    issuer: str = ISSUER,
    audience: str = AUDIENCE,
    expires_delta: timedelta = timedelta(minutes=5),
    key=PRIVATE_KEY,  # type: ignore[no-untyped-def]
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": subject,
            "iss": issuer,
            "aud": audience,
            "iat": now,
            "exp": now + expires_delta,
            "tenant_id": tenant_id,
            "email": "admin@test.example",
            "email_verified": True,
        },
        key,
        algorithm="RS256",
        headers={"kid": KEY_ID},
    )


def _client(world, monkeypatch, settings: Settings) -> TestClient:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(deps, "SessionLocal", world.session_factory)
    monkeypatch.setattr(deps, "PlatformSessionLocal", world.session_factory)
    monkeypatch.setattr(deps, "get_settings", lambda: settings)
    auth.clear_jwks_cache()
    return TestClient(app)


def _link_admin(world, subject: str = "oidc-admin") -> None:  # type: ignore[no-untyped-def]
    with world.session_factory() as session:
        session.info["bypass_tenant"] = True
        actor = session.get(UserIdentity, world.admin)
        assert actor is not None
        actor.oidc_subject = subject
        session.commit()


def test_valid_signature_issuer_audience_and_expiry_are_verified(world) -> None:
    settings = oidc_settings()
    claims = verify_oidc_token(token_for(tenant_id=str(world.tenant_a)), settings)
    assert claims["sub"] == "oidc-admin"
    assert claims["tenant_id"] == str(world.tenant_a)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"issuer": "https://wrong.example"}, "issuer"),
        ({"audience": "other-api"}, "audience"),
        ({"expires_delta": timedelta(seconds=-1)}, "expired"),
    ],
)
def test_invalid_standard_claims_are_rejected(world, kwargs, message) -> None:  # type: ignore[no-untyped-def]
    settings = oidc_settings()
    with pytest.raises(AuthenticationError, match=message):
        verify_oidc_token(token_for(tenant_id=str(world.tenant_a), **kwargs), settings)


def test_invalid_signature_is_rejected(world) -> None:
    settings = oidc_settings()
    with pytest.raises(AuthenticationError, match="signature"):
        verify_oidc_token(
            token_for(tenant_id=str(world.tenant_a), key=OTHER_PRIVATE_KEY), settings
        )


def test_oidc_subject_maps_to_provisioned_identity(world) -> None:
    _link_admin(world)
    settings = oidc_settings()
    claims = verify_oidc_token(token_for(tenant_id=str(world.tenant_a)), settings)
    with world.session_factory() as session:
        session.info["tenant_id"] = world.tenant_a
        authentication = resolve_oidc_actor(
            session,
            claims,
            requested_tenant_id=str(world.tenant_a),
            settings=settings,
        )
        assert authentication.actor.id == world.admin


def test_verified_email_linking_is_explicit_and_persisted(world) -> None:
    settings = oidc_settings(oidc_allow_verified_email_linking=True)
    claims = verify_oidc_token(token_for(subject="linked-by-email", tenant_id=str(world.tenant_a)), settings)
    with world.session_factory() as session:
        session.info["tenant_id"] = world.tenant_a
        authentication = resolve_oidc_actor(
            session,
            claims,
            requested_tenant_id=str(world.tenant_a),
            settings=settings,
        )
        assert authentication.actor.id == world.admin
        session.commit()
    with world.session_factory() as session:
        session.info["bypass_tenant"] = True
        actor = session.get(UserIdentity, world.admin)
        assert actor is not None
        assert actor.oidc_subject == "linked-by-email"


def test_token_tenant_claim_cannot_switch_request_tenant(world) -> None:
    _link_admin(world)
    settings = oidc_settings()
    claims = verify_oidc_token(token_for(tenant_id=str(world.tenant_b)), settings)
    with world.scoped_session() as session:
        with pytest.raises(AuthorizationError, match="tenant claim"):
            resolve_oidc_actor(
                session,
                claims,
                requested_tenant_id=str(world.tenant_a),
                settings=settings,
            )


def test_oidc_mode_does_not_fall_back_to_demo_header(world, monkeypatch) -> None:
    client = _client(world, monkeypatch, oidc_settings())
    response = client.get(
        "/api/v1/dashboard",
        headers={"X-Tenant-ID": str(world.tenant_a), "X-Actor-ID": str(world.admin)},
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_demo_mode_requires_explicit_actor_header(world, monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        auth_mode="demo",
        demo_mode=True,
        allowed_hosts=["testserver"],
        rate_limit_enabled=False,
    )
    client = _client(world, monkeypatch, settings)
    missing = client.get("/api/v1/dashboard", headers={"X-Tenant-ID": str(world.tenant_a)})
    accepted = client.get(
        "/api/v1/dashboard",
        headers={"X-Tenant-ID": str(world.tenant_a), "X-Actor-ID": str(world.admin)},
    )
    assert missing.status_code == 401
    assert accepted.status_code == 200


def test_fastapi_principal_uses_bearer_identity(world, monkeypatch) -> None:
    _link_admin(world)
    settings = oidc_settings()
    client = _client(world, monkeypatch, settings)
    response = client.get(
        "/api/v1/dashboard",
        headers={
            "X-Tenant-ID": str(world.tenant_a),
            "Authorization": f"Bearer {token_for(tenant_id=str(world.tenant_a))}",
        },
    )
    assert response.status_code == 200
    assert response.json()["counts"]["racks"] == 1


def test_invalid_bearer_receives_401_challenge(world, monkeypatch) -> None:
    client = _client(world, monkeypatch, oidc_settings())
    response = client.get(
        "/api/v1/dashboard",
        headers={
            "X-Tenant-ID": str(world.tenant_a),
            "Authorization": "Bearer not-a-token",
        },
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_production_configuration_rejects_demo_and_insecure_oidc() -> None:
    with pytest.raises(PydanticValidationError):
        Settings(
            _env_file=None,
            app_env="production",
            auth_mode="demo",
            demo_mode=True,
            require_https=False,
            oidc_issuer_url="http://identity.example/realms/sim",
            cors_origins=["http://app.example"],
        )
