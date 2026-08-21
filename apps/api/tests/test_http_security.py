from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.config import Settings
from app.http_security import SecurityBoundaryMiddleware


def security_app(settings: Settings) -> FastAPI:
    application = FastAPI()
    application.add_middleware(SecurityBoundaryMiddleware, settings=settings)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=list(settings.cors_methods),
        allow_headers=list(settings.cors_headers),
        expose_headers=list(settings.cors_expose_headers),
    )

    @application.get("/resource")
    def resource() -> dict[str, bool]:
        return {"ok": True}

    @application.post("/resource")
    def mutate() -> dict[str, bool]:
        return {"ok": True}

    @application.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


def base_settings(**overrides) -> Settings:  # type: ignore[no-untyped-def]
    values = {
        "allowed_hosts": ["testserver"],
        "cors_origins": ["https://app.example"],
        "rate_limit_enabled": True,
        "rate_limit_requests": 2,
        "rate_limit_window_seconds": 60,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_rate_limit_returns_429_and_health_is_exempt() -> None:
    client = TestClient(security_app(base_settings()))
    first = client.get("/resource")
    second = client.get("/resource")
    blocked = client.get("/resource")
    assert first.status_code == second.status_code == 200
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"]
    assert blocked.headers["x-ratelimit-limit"] == "2"
    assert blocked.headers["x-ratelimit-remaining"] == "0"
    for _ in range(4):
        assert client.get("/api/v1/health").status_code == 200


def test_cookie_authentication_requires_double_submit_csrf() -> None:
    settings = base_settings(
        rate_limit_enabled=False,
        cookie_auth_enabled=True,
        cors_allow_credentials=True,
    )
    client = TestClient(security_app(settings))
    client.cookies.set(settings.auth_cookie_name, "access-token")
    missing = client.post("/resource")
    client.cookies.set(settings.csrf_cookie_name, "csrf-value")
    mismatched = client.post("/resource", headers={settings.csrf_header_name: "other"})
    accepted = client.post("/resource", headers={settings.csrf_header_name: "csrf-value"})
    assert missing.status_code == 403
    assert mismatched.status_code == 403
    assert accepted.status_code == 200


def test_bearer_authentication_does_not_depend_on_cookie_csrf() -> None:
    settings = base_settings(
        rate_limit_enabled=False,
        cookie_auth_enabled=True,
        cors_allow_credentials=True,
    )
    client = TestClient(security_app(settings))
    client.cookies.set(settings.auth_cookie_name, "cookie-token")
    response = client.post("/resource", headers={"Authorization": "Bearer bearer-token"})
    assert response.status_code == 200


def test_https_enforcement_only_trusts_explicit_proxy() -> None:
    settings = base_settings(
        rate_limit_enabled=False,
        require_https=True,
        trusted_proxy_ips=["testclient"],
    )
    client = TestClient(security_app(settings))
    plain = client.get("/resource")
    forwarded = client.get("/resource", headers={"X-Forwarded-Proto": "https"})
    assert plain.status_code == 426
    assert forwarded.status_code == 200
    assert "max-age=" in forwarded.headers["strict-transport-security"]


def test_security_headers_and_strict_cors_are_present() -> None:
    settings = base_settings(rate_limit_enabled=False)
    client = TestClient(security_app(settings))
    response = client.get("/resource", headers={"Origin": "https://app.example"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.example"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    rejected = client.get("/resource", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in rejected.headers
