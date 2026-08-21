# Current Frontend Audit

**Audit date:** 2026-08-19 (Asia/Taipei)

| Item | Result |
|---|---|
| Active frontend | Static HTML + CSS + native ES Modules under `apps/web/` |
| Active React/Vue/Angular/Svelte | no |
| Active UI framework | none |
| Active WebGL library | none; custom native WebGL in `webgl-viewer.js` |
| Active third-party frontend dependencies | none declared |
| Isolated migration target | `apps/web-react/`: React/TypeScript/Refine/Ant Design source scaffold |
| New scaffold active in production | no; only mounted when a verified `dist/` exists |
| API access | `/api/v1`, tenant/project/location context, Bearer or explicit demo fallback |
| Code preserved | Cable Trace semantics, rack/route WebGL, field workflow and `/app/` |
| Main risk | framework work must not redefine tenant, cable, rack, workflow or audit semantics |

The React scaffold has source-level validation but no lockfile, package-backed typecheck, Vite build
or browser proof. Therefore the factual active frontend remains the legacy application.
