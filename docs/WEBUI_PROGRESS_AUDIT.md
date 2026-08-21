# WebUI migration audit

**Audit date:** 2026-08-19

| Area | State | Evidence | Confidence boundary |
|---|---|---|---|
| Legacy `/app/` | Preserved and active | HTML/CSS/ES Modules and custom WebGL unchanged | Existing syntax/API regression boundary |
| Isolated React project | Implemented source scaffold | `apps/web-react/package.json`, TS/TSX, Vite config | Source exists; dependency build not proven |
| Refine / Ant Design | Declared and wired in source | Refine provider, resources, Ant shell | npm packages not installed in this sandbox |
| API client | Implemented | shared tenant context, Bearer/demo adapter, normalized errors | helper smoke passes; browser integration not run |
| Dashboard | Connected in source | `/api/v1/dashboard` | no mock KPI; browser not run |
| Locations | Connected in source | `/api/v1/locations` | list page source parsed |
| Racks | Connected in source | `/api/v1/racks` + elevation | browser interaction not run |
| Cables / Trace | Connected in source | `/api/v1/cables/{id}/trace` | backend semantics unchanged |
| Cable Schedule | Connected in source | real CSV download | backend tested; React click not browser-tested |
| OIDC PKCE | Implemented helper | auth redirect/token exchange source | live Keycloak not run |
| Production build | NOT EXECUTED | npm registry timeout; no lockfile/dist | cannot mark foundation complete |
| Browser/a11y/mobile | NOT EXECUTED | no browser runtime | no 100% confidence |

`make dry-run` checks package declarations, parses all TS/TSX source and runs pure context/token
smoke tests. It intentionally does not label these checks as a real npm typecheck or production build.
