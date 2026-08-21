# Continuation Status — 2026-08-19

## Current completed batch

This batch follows the fixed P0 order:

1. OIDC JWT signature/issuer/audience/expiry validation and Principal mapping are implemented and
   covered by positive and negative tests.
2. A strict ordinary-role PostgreSQL Forced-RLS attack matrix is implemented. Its role checks pass,
   but the actual database matrix is NOT EXECUTED because real DSNs are unavailable.
3. Rate limiting, explicit CORS, Trusted Host, HTTPS/HSTS, trusted-proxy and cookie/CSRF boundaries
   are implemented and automated. Production shared-limit/TLS deployment proof remains.
4. An isolated React/TypeScript/Refine/Ant Design scaffold is present under `apps/web-react/` while
   the native `/app/` and custom WebGL remain active. npm/build/browser gates are NOT EXECUTED.

## Progress

- weighted master scope: **66.40%** (was 63.11%)
- remaining: **33.60%**
- DoD: **24 complete / 4 partial / 0 not complete**
- partial-credit DoD coverage: **92.86%**

## Latest local dry-run

- `make dry-run`: PASS in 14 seconds
- 56 tests passed; one real PostgreSQL runtime gate skipped
- 24 focused OIDC/security/RLS checks passed; same runtime gate skipped
- Python compile and native JS/WebGL syntax passed
- React declaration/source/context/token gate passed
- fresh SQLite migration, seed ×2 and seeded CSV export/audit passed
- npm dependency build, real PostgreSQL, live Keycloak, Docker/TLS and browser E2E remain NOT EXECUTED

## Repository policy

- GitHub Actions remain disabled and `.github/workflows` is absent
- progress and verification artifacts travel with source
- development uses local `make dry-run`
- validated changes are applied to `main` only by non-force fast-forward

## Publication status

The local batch is validated. The last readable remote `main` is
`2536ee32b76cc70d9e6efa172fd24881288568b6`. GitHub write actions were explicitly attempted,
but the current connector runtime returned `Resource not found`; remote `main` is therefore not
advanced. A non-force local Git pack and clean source archive are produced as recovery artifacts.
