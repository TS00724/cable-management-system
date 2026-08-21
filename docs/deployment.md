# 部署与运行

## 本地

`docker compose up --build` 设计为启动 PostgreSQL、Keycloak 和 API/UI。API 启动时执行
Alembic migration 和幂等 demo seed。当前执行环境没有 Docker runtime，因此该组合未在
本批实跑。

## 数据库角色

- `sim_app`：`NOSUPERUSER NOBYPASSRLS` 普通应用连接，必须受 forced RLS 约束
- `sim_platform`：控制面连接，显式 `BYPASSRLS`，但不是 superuser
- 初始化密码只用于开发；生产凭据必须来自 secret manager

真实数据库门禁：

```bash
export RLS_TEST_APPLICATION_DSN='postgresql://sim_app:...@localhost/sim'
export RLS_TEST_PLATFORM_DSN='postgresql://sim_platform:...@localhost/sim'
make postgres-rls
```

## 身份与 HTTP 边界

生产最少配置：

```text
APP_ENV=production
AUTH_MODE=oidc
DEMO_MODE=false
REQUIRE_HTTPS=true
OIDC_ISSUER_URL=https://identity.example/realms/sim
CORS_ORIGINS=https://sim.example
ALLOWED_HOSTS=sim.example
```

生产配置验证器拒绝 demo auth、HTTP issuer/origin、wildcard credentialed CORS、默认
bootstrap secret 和不安全 cookie 组合。反向代理 headers 只有来自 `TRUSTED_PROXY_IPS`
时才被信任。多副本部署必须把单进程 rate limiter 替换为共享原子后端。

## WebUI

- `/app/`：当前验证的原生 UI / WebGL
- `/app-next/`：仅当 `apps/web-react/dist/` 存在时挂载

在允许访问 npm registry 的环境执行：

```bash
cd apps/web-react
npm install
npm run typecheck
npm test
npm run build
```

在这些 gate 通过前，不应切换默认路由。

## 生产拓扑建议

```mermaid
flowchart TB
    LB[Ingress / TLS / WAF] --> API[API replicas]
    API --> PG[(Managed PostgreSQL + PITR)]
    API --> S3[(Private object storage)]
    API --> IDP[Enterprise OIDC]
    API --> RL[(Shared rate-limit backend)]
    API --> OBS[Logs / Metrics / Traces]
    Job[Worker / scheduler] --> PG
    Job --> S3
```

## 上线前门禁

- 真实 PostgreSQL non-owner forced-RLS matrix
- Keycloak login/refresh/logout/MFA/session-expiry E2E
- npm lockfile、typecheck、Vitest、Vite build 和 browser/a11y/mobile E2E
- TLS termination、proxy trust、shared rate limit 和 WAF 验证
- private object storage、malware scan 和 signed download
- SBOM、SAST、DAST、secret/container scan
- migration rollback、PITR、附件恢复和 RPO/RTO 演练
- Kubernetes probes/resources/PDB/rolling migration
- OpenTelemetry、SLO/告警、容量和故障注入
