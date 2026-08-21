# 安全设计与未闭合风险

## 已实现并自动验证

- OIDC JWT RS256/JWKS 签名、algorithm/kid、issuer、audience、expiry 和 required claims
- `oidc_subject` 主体映射和显式 opt-in verified-email linking
- token tenant claim 与请求 tenant 一致性
- OIDC 只建立身份，TenantMembership / AccessGrant 继续决定授权
- `oidc` 模式禁止回退到开发身份头，401 Bearer challenge
- 严格显式 CORS origins/methods/headers/exposed headers
- Trusted Host、HTTPS enforcement、可信代理边界和 HSTS
- 单进程固定窗口 rate limit、429/Retry-After/额度 headers
- cookie 身份 double-submit CSRF；Bearer 请求不依赖 cookie CSRF
- CSP、`nosniff`、frame、referrer、permissions 和 API no-store
- 生产设置拒绝 demo auth、HTTP OIDC/CORS、wildcard credentialed CORS、默认 bootstrap
  secret、不安全 SameSite=None 及关闭 HTTPS 的生产配置
- 既有租户隔离、端口占用、介质兼容、机架重叠、独立审批和 append-only audit 规则
- 普通应用数据库角色显式 `NOSUPERUSER NOBYPASSRLS`；平台角色单独 `BYPASSRLS`

## 仍需生产实证

1. 真实 Keycloak 登录、token refresh/logout、MFA 和 session expiry E2E。
2. 真实 PostgreSQL 普通应用角色执行 `make postgres-rls`。
3. 多副本环境使用共享原子限流后端，并验证 ingress / proxy IP 信任。
4. TLS termination、HSTS preload 和 secure-cookie 部署验证。
5. 私有对象存储、MIME/size 检查、malware scan 和短期签名下载。
6. 锁文件、SBOM、SAST、DAST、容器与 secret scan。
7. WebSocket/Webhook/import/export/search 同等租户边界和负载测试。

`X-Tenant-ID` 只是请求工作上下文，不是授权凭据。即使 token 含 tenant claim，主体仍必须
通过数据库中的成员关系或显式 AccessGrant 才能访问对应 tenant/project/location。
