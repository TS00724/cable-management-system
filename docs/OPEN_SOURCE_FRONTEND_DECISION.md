# Open-Source Frontend Decision

**Status:** Proposed / not yet implemented  
**Decision date:** 2026-08-19

## Decision

Adopt an incremental migration toward **React + TypeScript + Refine Core + Ant Design**, while keeping the current native JavaScript/WebGL application available as a regression reference until the migrated pages pass local dry-run and browser acceptance gates.

This decision does **not** assert that these dependencies are already installed. The current repository still contains the legacy dependency-free frontend only.

## Options considered

| Option | CRUD speed | FastAPI REST fit | Custom domain pages | TypeScript | 2D/3D flexibility | Migration risk | Decision |
|---|---|---|---|---|---|---|---|
| Refine Core + Ant Design | high | high | high | strong | high | medium | preferred |
| Ant Design Pro | high | high | medium/high | strong | high | medium | secondary |
| React-admin | high | high | high | strong | high | medium | viable alternative |
| Keep native JS | low | direct | high | none today | high | low short-term / high long-term | preserve as legacy only |

## Licensing rule

Before any package is committed, its exact version, license, repository URL, purpose and redistribution obligations must be entered in `THIRD_PARTY_NOTICES.md` and `docs/OPEN_SOURCE_INVENTORY.md`. Permissive licenses are preferred. No package is approved merely because it appears in this decision document.

## Guardrails

The migration may change presentation and client-side composition only. It must not redefine tenant isolation, authorization, port occupancy, cable compatibility, rack U conflicts, trace topology, test validity, approval, commissioning or audit immutability.

## Git / validation policy

Per current project direction, GitHub Actions are disabled. Development verification is performed with local dry-run commands and the evidence is recorded in `docs/DRY_RUN_STATUS.md` and `docs/VERIFICATION_REPORT.md` before `main` is advanced.
