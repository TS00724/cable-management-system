# API

FastAPI provides OpenAPI at `/api/v1/docs` and `/api/v1/openapi.json`. The API prefix is configurable through `API_PREFIX`.

## Implemented resources

| Domain | Endpoints |
|---|---|
| System | `GET /health`, `GET /ready` |
| Platform | `POST /platform/bootstrap` |
| Tenancy | current tenant, access-grant creation/revocation |
| Locations | list/create locations |
| Racks | list/create racks, rack elevation |
| Assets | list/create device templates and devices, list ports |
| Pathways | list/create pathways and segments |
| Cables | list/create cables, dynamic trace |
| Operations | list/create work orders, install, submit/list/approve tests |
| Standards | cable QR label, compliance report |
| Reporting | dashboard, global search, audit events, Cable Schedule CSV |
| Demo | context UUIDs when `DEMO_MODE=true` only |

## Cable Schedule CSV

`GET /api/v1/reports/cable-schedule.csv`

Query parameters:

| Parameter | Type | Meaning |
|---|---|---|
| `status` | CableStatus | optional installation-state filter |
| `project_id` | UUID | optional project filter |
| `q` | string, max 180 | searches identifier, media, construction, manufacturer and part number |
| `limit` | integer 1–10,000 | synchronous row limit; default 10,000 |

Response headers:

- `Content-Disposition`: generated CSV filename
- `Cache-Control: no-store`
- `X-Export-Row-Count`
- `X-Export-Total-Count`
- `X-Export-Truncated`

Authorization and safety:

- requires `report:export`
- current bulk-export slice only allows tenant members; a scoped contractor remains denied even if a future grant accidentally includes the permission
- all ORM reads retain tenant criteria, including totals and related objects
- export writes `report.cable_schedule.exported` to the immutable audit stream
- formula-prefixed text is neutralized for spreadsheet consumers

## Request context

Demo mode uses `X-Tenant-ID` and `X-Actor-ID`; scoped contractor requests also use `X-Project-ID` and `X-Location-ID`. Production must derive these values from a validated OIDC token and must not trust caller-supplied identity headers.

## API backlog

- uniform pagination envelopes, sorting/filter DSL, idempotency and ETag/If-Match
- asynchronous large exports and additional CSV/XLSX reports
- CSV/XLSX dry-run import with mapping preview and row errors
- secure file upload/download
- webhooks, SDK generation and full bundle/document/change endpoints
