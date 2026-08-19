# Current Frontend Audit

**Audit date:** 2026-08-19 (Asia/Taipei)  
**Fact source:** files currently present under `apps/web/` and the FastAPI static mount.

| Item | Result |
|---|---|
| Current frontend stack | Static HTML + CSS + native ES Modules |
| React | no |
| Vue | no |
| Angular | no |
| Svelte | no |
| UI Framework | none |
| WebGL library | none; custom native WebGL implementation in `webgl-viewer.js` |
| Third-party frontend dependencies | none declared; no `package.json` or lockfile in the audited workspace |
| Direct use of open-source Admin UI | no |
| Copied/vendor frontend code detected | none evidenced by package/vendor files or license headers in the audited workspace |
| License state | application code is repository-owned; future third-party dependencies must be recorded before adoption |
| API access | native `fetch` against `/api/v1`; demo identity uses `X-Tenant-ID`, `X-Actor-ID`, plus optional project/location headers |
| Static serving | FastAPI mounts `apps/web` at `/app` with `StaticFiles(..., html=True)` |
| Code to preserve | API semantics, Cable Trace rendering semantics, rack/route WebGL behavior, field workflow interactions |
| Code to replace incrementally | page shell, CRUD tables/forms, repeated fetch/error state logic, permission-aware navigation |
| Main risk | a framework migration must not change tenant, authorization, cable, rack, workflow, or audit semantics |

## Evidence

- `apps/web/index.html` contains the complete application shell and no framework bootstrap.
- `apps/web/app.js` imports only the local `./webgl-viewer.js` module and calls the existing FastAPI API directly.
- `apps/web/webgl-viewer.js` implements shaders, camera math, picking and rack/route rendering directly with browser WebGL.
- The repository currently has no `package.json`, lockfile, TypeScript source, React source or Vite configuration.

## Migration status

The open-source WebUI migration is **not yet implemented in the current factual workspace**. The next frontend milestone is to create an isolated React/TypeScript scaffold while preserving the existing UI as the regression reference.
