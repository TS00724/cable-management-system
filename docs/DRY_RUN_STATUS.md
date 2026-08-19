# Local Dry-Run Status

**Executed:** 2026-08-19 14:56 +08:00  
**Policy:** GitHub Actions are disabled; development gates run locally before `main` is advanced.

| Gate | Command / method | Result |
|---|---|---|
| Backend tests | `cd apps/api && PYTHONPATH=. pytest -q` | PASS — 27 passed |
| Python compile | `cd apps/api && PYTHONPATH=. python -m compileall -q app migrations` | PASS |
| Frontend syntax | `node --check apps/web/app.js` | PASS |
| WebGL syntax | `node --check apps/web/webgl-viewer.js` | PASS |
| Fresh schema | Alembic upgrade against `/tmp/sim-dry-run.db` | PASS |
| Seed idempotency | `python -m app.seed` twice against the same fresh SQLite database | PASS — stable identifiers |

## Explicitly not executed

- real PostgreSQL non-owner RLS runtime test
- Docker Compose boot
- Keycloak/OIDC login and JWT validation
- browser/WebGL E2E
- load, accessibility and DAST gates

A PASS above applies only to the named dry-run gate and must not be used to claim adjacent unexecuted functionality is complete.
