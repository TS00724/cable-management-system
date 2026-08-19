# API

FastAPI 自动提供 OpenAPI (`/docs`, `/openapi.json`)。演示 API 前缀为 `/api/v1`。

## 已实现资源

| Domain | Endpoints |
|---|---|
| System | `GET /health`, `GET /ready` |
| Platform | `POST /platform/bootstrap` |
| Tenancy | `GET /tenants/current`, `POST /access-grants`, revoke grant |
| Locations | list/create locations |
| Racks | list/create racks, rack elevation |
| Assets | list/create device templates and devices, list ports |
| Pathways | list/create pathway + segments |
| Cables | list/create cables, dynamic trace |
| Operations | list/create work orders, install, submit/list/approve tests |
| Standards | create cable QR label, compliance report |
| Reporting | dashboard, global search, audit events |
| Demo | context UUIDs in demo mode only |

## 请求上下文

演示模式使用：

- `X-Tenant-ID`
- `X-Actor-ID`
- 承包商范围请求还使用 `X-Project-ID`, `X-Location-ID`

生产必须以 OIDC token 建立这些上下文，不能直接信任请求头。

## API 未完成项

- 全资源统一分页 envelope、排序、过滤 DSL
- Idempotency-Key
- If-Match/ETag 乐观并发 API
- 批量导入/导出和异步作业
- 文件上传/下载
- Webhooks
- SDK 生成
- 完整组织、用户、bundle、circuit、document、change-request endpoints
