# Verification Report

**Date:** 2026-08-19  
**Scope:** factual continuation workspace in `/mnt/data/sim-continued-work`  
**Repository validation policy:** GitHub Actions disabled; local development dry-run only.

## Current local dry-run — 2026-08-19 14:56 +08:00

These gates were re-executed immediately before preparing the direct `main` update.

| Gate | Command / method | Result |
|---|---|---|
| Backend tests | `cd apps/api && PYTHONPATH=. pytest -q` | PASS — 27 passed |
| Python compile | `cd apps/api && PYTHONPATH=. python -m compileall -q app migrations` | PASS |
| Browser module syntax | `node --check apps/web/app.js` | PASS |
| WebGL module syntax | `node --check apps/web/webgl-viewer.js` | PASS |
| Fresh schema | Alembic upgrade against empty `/tmp/sim-dry-run.db` | PASS |
| Seed idempotency | `python -m app.seed` twice against the same fresh SQLite DB | PASS — stable core demo identifiers |

`make dry-run` now executes the same local gate set. `make verify` remains an alias to preserve developer muscle memory. No GitHub workflow is used or retained.

## Historical verified evidence retained from the prior vertical-slice release

The following gates were executed and recorded in the previous verified build; they were **not re-run in the repository-policy-only dry-run above**.

| Gate | Historical result |
|---|---|
| API/static smoke | PASS — 10/10 HTTP 200 |
| Trace semantics | PASS — exact sequence shown below |
| Exact identifier search | PASS — target cable ranked first in tenant scope |
| Python wheel build | PASS — `pip wheel --no-build-isolation --no-deps` |

## Exact historical trace result

```text
port
→ cable
→ port
→ internal_mapping
→ port
→ cable
→ port
```

This path is produced from persisted `CableTermination` and `PortMapping` rows and includes ordered route segment coordinates for the selected horizontal cable.

## Security and negative cases in the 27-test suite

- Tenant A query cannot see Tenant B rack
- Tenant A direct object lookup returns not found for Tenant B rack
- cross-tenant write is rejected before flush
- contractor grant only works for matching project/location descendant
- expired grant is denied
- occupied port cannot receive a second cable
- incompatible media is rejected
- rack U overlap and reserved position are rejected
- tester cannot approve own restricted test
- failed test cannot be commissioned
- audit update/delete are rejected
- PostgreSQL RLS migration table coverage is checked

## Not executed in this environment

| Gate | Reason | Consequence |
|---|---|---|
| Real PostgreSQL forced-RLS runtime | No PostgreSQL/Docker runtime | RLS remains 85% confidence, not 100% |
| Docker Compose boot | Docker unavailable | Compose is configuration-reviewed only |
| Keycloak login/JWT | No integrated identity runtime; JWT validation not implemented | Identity is not production-complete |
| Playwright/browser/WebGL visual E2E | No real browser/GPU automation | UI syntax is proven; visual behavior is not fully certified |
| Load/soak/accessibility/DAST | Tooling and scope not present | Enterprise hardening remains backlog |

## Audit interpretation

“PASS” proves the stated gate only. It does not upgrade adjacent untested functionality to 100% confidence. Historical PASS entries are explicitly distinguished from the current dry-run so that the progress record does not overstate what was re-executed.
