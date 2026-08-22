# Runtime P0 Evidence — 2026-08-22

## Environment discovery

The current execution environment does not provide a PostgreSQL service, Docker/Podman, configured `RLS_TEST_*` DSNs, or a reachable Keycloak runtime. The existing Forced-RLS matrix and OIDC validation tests remain code evidence only; neither external-service gate is promoted to PASS.

## Shared atomic rate limiting

`PYTHONPATH=apps/api:. python scripts/runtime_shared_rate_limit_smoke.py` launched four independent processes against one shared SQL database. The first three consumed the quota and the fourth was denied. Result: **PASS**.

## TLS / proxy / CSRF evidence

Automated tests continue to cover direct HTTPS, HSTS, strict CORS, rejection of untrusted forwarded protocol headers, trusted-proxy handling, cookie double-submit CSRF and Bearer-token independence from cookie CSRF. No external ingress/TLS terminator exists in this environment, so deployment-level proof remains pending.

## Explicitly not executed

- real PostgreSQL ordinary-role Forced-RLS attack matrix
- live Keycloak PKCE, refresh, logout, MFA and session expiry
- production multi-replica load and failure testing
- external TLS termination and secure-cookie browser flow
