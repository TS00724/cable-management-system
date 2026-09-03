# PR7 — Fiber splice foundation: implementation and verification

Date: 2026-09-03 (Asia/Taipei)
Base: `2c456e0039982fe406f45794e954dcad9e8260ca`
Policy: local verification only. No GitHub Actions or workflow files are introduced.

## Baseline correction

PR #6's description says CRUD, attachments and Fiber were delivered, but its actual changed-file patch consists of 13 temporary write-probe files. The main branch's `models.py` has no Fiber models. This batch starts from the actual main source, not the PR description. Earlier global completion percentages are not used as verified evidence and are not increased by this batch.

Reference: `https://github.com/TS00724/cable-management-system/pull/6/files`

The local shell cannot clone GitHub. Required baseline files were read through the GitHub connector and reconstructed with matching Git blob SHAs. The following original source was verified before modification or use:

| Path | Original blob SHA |
|---|---|
| apps/api/app/models.py | de236f7b7dc8c1d14d0e4a973791b844e734871a |
| apps/api/app/security.py | d05ff552fa597a075524be075b0e2d009bb90aab |
| apps/api/app/audit.py | f1d2d79d9e5a26ef0e4d5a409818a4b2d49fca4a |
| apps/api/app/db.py | 2ccfb0ab73fa84079e68be837ed55c4f2975696c |
| apps/api/app/config.py | d86503824ad92d1a0acbe42a4d23b82b17cd5884 |
| apps/api/app/main.py | e452bffe518e28eb0d23a3c16fc5b74130c158fe |
| apps/api/migrations/env.py | 671bc360349b91e3f868b2c9ed53d5cf5b59b504 |
| apps/api/tests/test_migration_policy_coverage.py | 66202eb7e1fb40584b803e75e1e4dd3234fca490 |
| apps/web-react/src/App.tsx | f23b2aa3495293c3c0b48fbf763f2c2579f065c4 |
| apps/web-react/src/components/AppShell.tsx | d6aa8fda4c032a979bff7f6fcecca606e7d2aad8 |
| pyproject.toml | 046a323842699e6914c075518904e701f6d3ffcd |

## Delivered slice

Six persistent tenant-owned tables: FiberBundle, FiberStrand, FiberCassette, FiberCassetteSlot, FiberSplice and FiberSpliceEnd. One bundle initializes all strands of a project-assigned fiber cable (1–576). A cassette belongs to a project and an existing device, with 1–288 numbered splice positions. These positions are **splice-tray slots**, not chassis module bays.

Composite tenant foreign keys prohibit cross-tenant parent references. A partial unique index permits only one active splice per slot. Normalized endpoint claims prohibit duplicate `(tenant, strand, side)` occupancy regardless of payload orientation. Releasing preserves the splice history row and audited endpoint identities while removing active claims.

Every operation re-evaluates real membership/grants against the resource's actual project and device location. Request context headers or cached Principal permissions are not treated as resource authority. A location-scoped contractor can operate a local cassette but cannot initialize or trace an entire cable without a project-wide grant. Cross-project splices are deliberately unsupported in this slice.

All splice/release writers acquire the same actual-project write mutex before topology reads. Compare-and-swap slot versions reject stale writes. A failed mutation, including audit failure, must roll back the transaction. The API owns commit/rollback and returns generic 409 for integrity conflicts and retryable 503 for database operational failures.

Tracing walks actual strand/splice edges with explicit A/B orientation, cycle detection and a hard 256-strand limit. The reported loss is only the sum of traversed splice losses, not total optical-link attenuation. Mutation rejects topology whose safety cannot be established within the traversal bound.

Nine API routes are mounted under `/api/v1/fiber` using the host application's existing database and authentication dependencies. The React route `/app-next/fiber` provides bundle initialization/lookup, cassette creation/list/loading, slot splice/release and bounded trace. It resets loaded state on scope changes and blocks further mutation after a conflict or uncertain write outcome until a successful reload.

## Executed gates

```bash
PYTHONPATH=apps/api python -m pytest \
  tests/fiber apps/api/tests/test_migration_policy_coverage.py -q
node scripts/check_fiber_ui.cjs
python -m compileall -q apps/api/app apps/api/migrations tests/fiber
```

| Gate | Result | Exact boundary |
|---|---|---|
| Domain, authorization, HTTP router, migration and policy tests | 47 passed | Real SQLite, original ORM guards and real service; HTTP identity dependency injected |
| Concurrent topology writers | Passed | Two independent SQLAlchemy sessions/threads; complementary splices cannot jointly create a cycle on SQLite |
| Raw SQL integrity | Passed | Cross-tenant composite FKs, active slot and endpoint uniqueness |
| Revision 004 roundtrip | Passed | Existing ORM schema → downgrade 004 → upgrade 004; legacy Cable rows preserved; model/schema diff empty; service writes after upgrade |
| PostgreSQL offline SQL | Passed | All six ENABLE/FORCE RLS policies, USING/WITH CHECK, parent-index order and reverse drop order |
| Python compile | Passed | Reconstructed and changed Python source, not a full application startup |
| TypeScript/TSX syntax | 4 files passed | Transpilation diagnostics, not a complete React dependency typecheck |
| Frontend pure helper strict typecheck and assertions | Passed | UUID validation, version validation, scope keys, conflict/status handling and route source checks |

The tests are intentionally under `tests/fiber`; `pyproject.toml` includes this directory in normal pytest discovery. The original RLS coverage test unions migration 002 and migration 004 tables. Migration 002 is not rewritten to refer to tables that did not exist at that revision.

## Not executed / not completed

The full existing application regression suite, a full initial Alembic revision-chain upgrade, full React/Ant Design typecheck, Vite build and real-browser E2E were **not executed**. No full-app OIDC/middleware result is inferred from the isolated HTTP router tests.

Real PostgreSQL ordinary-role RLS/locking, live Keycloak lifecycle/MFA, MinIO/S3/ClamAV and PITR/RPO/RTO were **not executed**. Offline SQL checks are not a substitute for PostgreSQL runtime proof.

Fiber port terminations, chassis cassette bays, Pair/Channel, OTDR, Breakout and the generic copper/fiber Cable Trace integration remain unfinished. No million-node or production load claim is made. Read-side traces are bounded live views; this batch does not establish snapshot consistency during concurrent external topology edits.

## Apply and rollback

Back up the database and test on an isolated copy before deployment. Run the existing Alembic upgrade command with the migration role; deploy application code only after revision `200000000004` succeeds. The new tables need the existing deployment's ordinary application-role DML grants; do not grant ownership, SUPERUSER or BYPASSRLS to make a failing gate pass.

Application permissions are `fiber:read` and `fiber:write`; existing wildcard owners are supported. Do not change production roles or seed access automatically.

Rolling back the application alone leaves the additive tables intact. `alembic downgrade 200000000003` **destroys Fiber data** and should only be run with an approved backup/restore plan. It preserves the pre-existing core tables. No production migration or destructive restore drill was executed in this session.

## Next checkpoint

The backend foundation has passed its named local gates; the full Fiber milestone is still partial. The next checkpoint is full host-app and browser verification of this slice, followed by port-occupancy integration and Pair/Channel, OTDR, Breakout and generic trace. Do not skip to Floor Plan while reporting the whole Fiber milestone complete.

Nine-stage status is tracked in `PR7_PROGRESS.csv`. The historical root `WORK_PROGRESS.xlsx` has not been recalculated in this batch.
