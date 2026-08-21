# Local Dry-Run Status

**Executed:** 2026-08-19 19:27 +08:00  
**Policy:** GitHub Actions are disabled; development gates run locally before `main` is advanced.

| Gate | Command / method | Result |
|---|---|---|
| Full backend/security suite | `cd apps/api && PYTHONPATH=.:../.. pytest -q` | PASS — 56 passed, 1 skipped |
| Focused P0 matrix | OIDC + HTTP security + PostgreSQL role/matrix tests | PASS — 24 passed, 1 skipped |
| Python compile | `python -m compileall -q app migrations` | PASS |
| Legacy frontend syntax | `node --check apps/web/app.js` | PASS |
| Legacy WebGL syntax | `node --check apps/web/webgl-viewer.js` | PASS |
| React source gate | package declaration + all TS/TSX parse + context/token smoke | PASS |
| Fresh schema | Alembic upgrade against disposable `/dev/shm` SQLite database | PASS |
| Seed idempotency | `python -m app.seed` twice | PASS — 9 stable identifiers |
| Seeded Cable Schedule | fresh Northstar DB → CSV + audit | PASS — 3 rows, audit persisted |
| Total `make dry-run` | one complete command | PASS — 14 seconds |

## Explicitly not executed

- real PostgreSQL non-owner Forced-RLS attack matrix: DSNs are not configured
- npm dependency installation, real package typecheck, Vitest and Vite production build: registry request timed out
- live Keycloak PKCE login, refresh/logout, MFA and session-expiry E2E
- Docker Compose boot and TLS/reverse-proxy integration
- browser/WebGL/accessibility/mobile E2E
- load, SAST, DAST and recovery gates

The skipped Pytest item is exactly the real PostgreSQL matrix. A source-level React gate is not a
substitute for dependency-backed typecheck/build. A PASS above applies only to the named boundary.
