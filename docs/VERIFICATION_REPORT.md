# Verification Report

**Date:** 2026-08-19 19:27 +0800  
**Scope:** P0 identity, database-boundary proof harness, HTTP security and isolated React scaffold

## Executed gates

| Gate | Command | Result |
|---|---|---|
| Full local gate | `make dry-run` | PASS — complete in 14 seconds |
| Python/API/domain/security | `PYTHONPATH=.:../.. pytest -q` | PASS — 56 passed, 1 skipped |
| Focused P0 | `pytest -q test_auth_oidc.py test_http_security.py test_postgres_rls_matrix.py` | PASS — 24 passed, 1 skipped |
| Python compile | `python -m compileall -q app migrations` | PASS |
| Legacy JS/WebGL | two `node --check` commands | PASS |
| React source gate | `scripts/check-web-react-source.sh` | PASS |
| Fresh SQLite migration | `alembic upgrade head` | PASS |
| Seed idempotency | same fresh DB seeded twice | PASS — 9 stable IDs |
| Seeded export | `scripts/seeded-export-smoke.py` | PASS — 3 rows and one audit event |

## P0 #1 — OIDC JWT and Principal mapping

Automated tests prove:

- RS256 cryptographic signature and `kid` selection against JWKS
- algorithm allow-list
- exact issuer and audience
- expiry and required `sub`/`iss`/`aud`/`exp` claims
- unknown key, malformed token and invalid signature rejection
- `UserIdentity.oidc_subject` mapping
- opt-in verified-email linking
- token tenant claim must match requested tenant
- `AUTH_MODE=oidc` does not fall back to `X-Actor-ID`
- HTTP 401 with `WWW-Authenticate: Bearer`
- after authentication, existing TenantMembership / AccessGrant Principal authorization remains authoritative

Live Keycloak login/token lifecycle/MFA was not executed.

## P0 #2 — PostgreSQL Forced-RLS runtime matrix

`scripts/postgres_rls_attack_matrix.py` refuses an application connection that is superuser,
`BYPASSRLS`, table owner, or connected to a table without both RLS and FORCE RLS. It then attempts
Tenant A list/direct lookup/update/delete/insert against Tenant B and proves own-tenant insert.
Role-precondition tests pass. `make postgres-rls` returned `NOT_EXECUTED` because the two required
PostgreSQL DSNs are not configured; therefore runtime RLS confidence is not 100%.

## P0 #3 — HTTP security boundary

Automated tests cover:

- fixed-window 429 response and rate-limit headers
- health/readiness exemption
- explicit CORS allow-origin behavior
- Trusted Host integration in the application
- HTTPS enforcement with only explicitly trusted proxy headers
- HSTS on secure requests
- cookie double-submit CSRF for unsafe methods
- Bearer requests do not depend on cookie CSRF
- CSP, no-store, nosniff, frame, referrer and permissions headers
- production settings reject demo auth, insecure issuer/origins, wildcard credentialed CORS,
  default bootstrap key, unsafe SameSite=None and non-HTTPS production mode

The limiter is intentionally single-process. A shared atomic backend and real proxy/TLS deployment
remain production gates.

## P0 #4 — Isolated React / Refine scaffold

`apps/web-react/` declares React, TypeScript, Vite, Refine Core, Refine Ant Design, Ant Design,
React Router and TanStack Query. It has one request context, bearer/demo adapter, normalized errors,
PKCE helper, enterprise shell and real API pages for Dashboard, Locations, Rack elevation, Cables,
Cable Trace and Cable Schedule. The native `apps/web/` and `webgl-viewer.js` are unchanged.

The npm registry attempt timed out and produced no lockfile. Consequently real package-backed
TypeScript typecheck, Vitest, Vite build, `/app-next/` serving and browser E2E are **NOT EXECUTED**.
The passing source gate only proves declarations, TS/TSX parse, context roundtrip and token helpers.

## Confidence boundary

No unexecuted PostgreSQL, npm, Keycloak, browser, Docker, TLS proxy, load, accessibility or DAST
check is represented as PASS. See `docs/DRY_RUN_STATUS.md` and `WORK_PROGRESS.xlsx` for the exact
module scores and remaining work.


## GitHub publication gate

- Last readable remote `main`: `2536ee32b76cc70d9e6efa172fd24881288568b6`.
- GitHub Actions remain disabled and no workflow is introduced.
- Branch/file/ref write actions were explicitly attempted after user authorization, but the current
  connector runtime returned `Resource not found` for the write resources.
- Result: local branch/main delivery objects are prepared; remote `main` is **NOT ADVANCED** in this run.
