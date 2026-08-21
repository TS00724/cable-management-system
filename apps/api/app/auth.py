from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.exceptions import AuthenticationError, AuthorizationError
from app.models import UserIdentity


@dataclass(frozen=True)
class OidcAuthentication:
    actor: UserIdentity
    claims: dict[str, Any]


class _JwksCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[tuple[str, str | None, str | None], tuple[float, dict[str, Any]]] = {}

    def get(self, key: tuple[str, str | None, str | None]) -> dict[str, Any] | None:
        with self._lock:
            item = self._values.get(key)
            if not item:
                return None
            expires_at, value = item
            if expires_at <= time.monotonic():
                self._values.pop(key, None)
                return None
            return value

    def put(self, key: tuple[str, str | None, str | None], value: dict[str, Any], ttl: int) -> None:
        with self._lock:
            self._values[key] = (time.monotonic() + max(ttl, 0), value)

    def clear(self) -> None:
        with self._lock:
            self._values.clear()


_JWKS_CACHE = _JwksCache()


def clear_jwks_cache() -> None:
    _JWKS_CACHE.clear()


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, separator, value = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not value.strip():
        raise AuthenticationError("Authorization header must use Bearer authentication")
    return value.strip()


def _fetch_json(url: str, *, timeout: float) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            response = client.get(url, headers={"Accept": "application/json"})
        if 300 <= response.status_code < 400:
            raise AuthenticationError("OIDC metadata redirects are not accepted")
        response.raise_for_status()
        payload = response.json()
    except AuthenticationError:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise AuthenticationError("Unable to load OIDC metadata") from exc
    if not isinstance(payload, dict):
        raise AuthenticationError("OIDC metadata must be a JSON object")
    return payload


def _load_jwks(settings: Settings) -> dict[str, Any]:
    cache_key = (settings.oidc_issuer_url, settings.oidc_jwks_url, settings.oidc_jwks_json)
    cached = _JWKS_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if settings.oidc_jwks_json:
        try:
            payload = json.loads(settings.oidc_jwks_json)
        except json.JSONDecodeError as exc:
            raise AuthenticationError("OIDC_JWKS_JSON is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise AuthenticationError("OIDC_JWKS_JSON must be an object")
    else:
        jwks_url = settings.oidc_jwks_url
        if not jwks_url:
            discovery_url = f"{settings.oidc_issuer_url.rstrip('/')}/.well-known/openid-configuration"
            discovery = _fetch_json(discovery_url, timeout=settings.oidc_http_timeout_seconds)
            if discovery.get("issuer") != settings.oidc_issuer_url:
                raise AuthenticationError("OIDC discovery issuer does not match configuration")
            jwks_url = discovery.get("jwks_uri")
            if not isinstance(jwks_url, str) or not jwks_url:
                raise AuthenticationError("OIDC discovery document has no jwks_uri")
        payload = _fetch_json(jwks_url, timeout=settings.oidc_http_timeout_seconds)

    keys = payload.get("keys")
    if not isinstance(keys, list) or not keys:
        raise AuthenticationError("OIDC JWKS contains no keys")
    _JWKS_CACHE.put(cache_key, payload, settings.oidc_jwks_cache_seconds)
    return payload


def verify_oidc_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Malformed OIDC token") from exc

    algorithm = header.get("alg")
    kid = header.get("kid")
    if algorithm not in settings.oidc_algorithms:
        raise AuthenticationError("OIDC signing algorithm is not allowed")
    if not isinstance(kid, str) or not kid:
        raise AuthenticationError("OIDC token has no key identifier")

    key_data = next((item for item in _load_jwks(settings)["keys"] if item.get("kid") == kid), None)
    if key_data is None:
        # A rotation may have occurred. Clear once and retry the configured source.
        clear_jwks_cache()
        key_data = next((item for item in _load_jwks(settings)["keys"] if item.get("kid") == kid), None)
    if key_data is None:
        raise AuthenticationError("OIDC signing key was not found")

    try:
        key = jwt.PyJWK.from_dict(key_data, algorithm=algorithm).key
        claims = jwt.decode(
            token,
            key=key,
            algorithms=list(settings.oidc_algorithms),
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer_url,
            leeway=settings.oidc_clock_skew_seconds,
            options={"require": ["sub", "iss", "aud", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("OIDC token has expired") from exc
    except jwt.InvalidIssuerError as exc:
        raise AuthenticationError("OIDC token issuer is invalid") from exc
    except jwt.InvalidAudienceError as exc:
        raise AuthenticationError("OIDC token audience is invalid") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("OIDC token signature or claims are invalid") from exc

    if not isinstance(claims, dict) or not isinstance(claims.get("sub"), str):
        raise AuthenticationError("OIDC token subject is invalid")
    return claims


def resolve_oidc_actor(
    session: Session,
    claims: dict[str, Any],
    *,
    requested_tenant_id: str,
    settings: Settings | None = None,
) -> OidcAuthentication:
    settings = settings or get_settings()
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AuthenticationError("OIDC token subject is missing")

    tenant_claim = claims.get(settings.oidc_tenant_claim)
    if tenant_claim is not None and str(tenant_claim) != str(requested_tenant_id):
        raise AuthorizationError("OIDC tenant claim does not match the requested tenant")

    actor = session.scalar(select(UserIdentity).where(UserIdentity.oidc_subject == subject))
    if actor is None and settings.oidc_allow_verified_email_linking:
        email = claims.get("email")
        verified = claims.get("email_verified") is True
        if verified and isinstance(email, str) and email.strip():
            actor = session.scalar(
                select(UserIdentity).where(func.lower(UserIdentity.email) == email.strip().lower())
            )
            if actor is not None:
                if actor.oidc_subject and actor.oidc_subject != subject:
                    raise AuthenticationError("Identity is already linked to another OIDC subject")
                actor.oidc_subject = subject
                session.flush()
    if actor is None or not actor.active:
        raise AuthenticationError("OIDC identity is not provisioned or is inactive")
    return OidcAuthentication(actor=actor, claims=claims)
