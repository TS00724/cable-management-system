# Incremental React / Refine WebUI migration

## Factual state

- `apps/web/` remains the active, previously verified HTML/CSS/ES Module application.
- `apps/web/webgl-viewer.js` remains the rack/selected-route WebGL regression reference.
- `apps/web-react/` is an isolated React/TypeScript migration target.
- FastAPI mounts `/app-next/` only when a real `apps/web-react/dist/` exists.
- `/app/` remains the default route; no big-bang replacement occurred.

## Implemented scaffold

- React + TypeScript + Vite project definition
- Refine Core, Refine Ant Design integration, React Router and TanStack Query declarations
- Ant Design responsive enterprise shell
- shared tenant/project/location request context
- bearer token plus explicit demo migration fallback
- normalized API error and request-ID handling
- Authorization Code + PKCE helper
- real Dashboard, Location, Rack elevation, Cable list, Cable Trace and Cable Schedule API calls
- loading, empty, error and 404 states
- direct link to the legacy WebGL UI
- source-level TypeScript parse and context/token smoke gate

No infrastructure KPI is hardcoded in the new pages.

## Not yet verified

The npm registry request timed out. Therefore dependency installation and lockfile generation,
real package-backed TypeScript typecheck, Vitest, Vite production build, `/app-next/` serving,
browser/responsive/accessibility and OIDC E2E are **NOT EXECUTED**. Until those gates pass, the
scaffold is not the active production UI and WebUI Foundation is not marked complete.
