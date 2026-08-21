# Structured Infrastructure Manager

面向园区、数据中心和结构化布线项目的多租户物理基础设施事实源。此仓库实现了主构建文档要求的第一条可运行纵向链路：

`Tenant → Campus → Building → TR → Rack → Device Template → Device → Port → Cable → Pathway → Trace → Work Order → Test → Approval → Audit`

## 当前交付

- FastAPI、SQLAlchemy、Alembic 模块化单体
- 显式组织、租户、项目、位置、机架、设备、端口、路径、线缆、工单、测试、标签和审计模型
- 应用层租户过滤与写入保护；PostgreSQL 强制 RLS 迁移
- 客户租户成员与跨组织、按项目/位置/时间范围授权的承包商模型
- 端口占用、介质兼容、机架 U 位冲突等物理约束
- 穿越 patch-panel 前后端口映射的递归物理线缆追踪
- TIA-606-D 可配置基线、标识符模板、QR 标签及辅助合规报告
- 安装、测试、独立审批、投入使用和追加式审计工作流
- 数据驱动的运营界面、原生 WebGL 机架和路径高亮
- Northstar University、Metro Structured Cabling Ltd 和第二租户隔离演示数据
- OIDC JWT/JWKS 验证、Principal 映射、严格 CORS/TLS、rate limit 与 cookie/CSRF 边界
- 普通 PostgreSQL 应用角色 Forced-RLS 攻击矩阵（脚本已实现，真实 runtime 待执行）
- 隔离的 React/TypeScript/Refine/Ant Design 迁移 scaffold；原生 UI 与 WebGL 保留
- 自动化安全、API、迁移和业务规则测试
- 经审计的租户隔离 Cable Schedule CSV 导出：真实 A/B 端接、位置、项目与路径字段

完整模块审核见 [`docs/WORK_PROGRESS.md`](docs/WORK_PROGRESS.md)，机器可筛选版见仓库根目录 `WORK_PROGRESS.xlsx`。

## 本地快速运行（SQLite）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cd apps/api
export PYTHONPATH=.
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

打开当前验证 UI：`http://localhost:8000/app/`；OpenAPI：`http://localhost:8000/api/v1/docs`。只有 `apps/web-react/dist/` 真实存在时，迁移目标才挂载到 `http://localhost:8000/app-next/`。

## Docker Compose（PostgreSQL + Keycloak + API/UI）

```bash
cp .env.example .env
docker compose up --build
```

服务：

- 应用与 UI：`http://localhost:8000`
- OpenAPI：`http://localhost:8000/docs`
- Keycloak：`http://localhost:8080`

`.env.example` 中的密码只适用于本地开发。生产环境必须使用密钥管理器、TLS、独立数据库角色和外部对象存储。

## 验证

```bash
make dry-run
```

该命令运行：

- Pytest 单元、集成和安全测试
- Python 编译检查
- 原生前端 ES Module / WebGL 语法检查
- React/TypeScript package 声明、全部源文件解析、tenant context 与 token helper smoke
- 空 SQLite 数据库 Alembic migration
- 同一数据库 seed 两次并核对关键 ID
- 使用 Northstar seed 数据下载 Cable Schedule，并核对 CSV 与审计事件

另可从空数据库执行：

```bash
cd apps/api
DATABASE_URL=sqlite+pysqlite:///./verification.db \
PLATFORM_DATABASE_URL=sqlite+pysqlite:///./verification.db \
MIGRATION_DATABASE_URL=sqlite+pysqlite:///./verification.db \
alembic upgrade head

DATABASE_URL=sqlite+pysqlite:///./verification.db \
PLATFORM_DATABASE_URL=sqlite+pysqlite:///./verification.db \
python -m app.seed
```

## Cable Schedule 导出

租户成员必须具备独立的 `report:export` 权限。当前同步 CSV 端点支持状态、项目、关键字和条数限制；服务端应用租户过滤，并写入追加式审计事件。

```bash
curl -OJ \
  -H "X-Tenant-ID: <tenant-uuid>" \
  -H "X-Actor-ID: <tenant-owner-uuid>" \
  "http://localhost:8000/api/v1/reports/cable-schedule.csv?status=in_service&limit=10000"
```

CSV 对可能触发电子表格公式的文本值进行前缀中和。当前边界是最多 10,000 行的同步导出；异步大批量作业、XLSX 和其他报表仍在 backlog。

## OIDC 与演示身份

生产请求使用 `Authorization: Bearer <JWT>`。API 校验 signature、algorithm/kid、issuer、audience、expiry 和 required claims，以 `UserIdentity.oidc_subject` 映射身份，再执行 TenantMembership / AccessGrant 授权。详见 [`docs/authentication.md`](docs/authentication.md)。

开发迁移阶段可使用 `AUTH_MODE=hybrid` 和 `DEMO_MODE=true`。

`/api/v1/demo/context` 仅在 `DEMO_MODE=true` 时返回演示 UUID。浏览器 UI 使用请求头模拟三种主体：

- Alice Admin：Northstar Tenant Owner
- Tina Technician：Metro 承包商现场技术员，仅限 Engineering Building Upgrade Project
- Sam Supervisor：Northstar Infrastructure Manager

生产环境必须使用 `AUTH_MODE=oidc`、`DEMO_MODE=false` 和 HTTPS。演示请求头不能成为生产身份边界。

## 重要边界

本仓库是经过测试的第一条纵向链路，不是主构建文档全部范围的最终商业版本。尚未完成的重点包括真实 Keycloak token lifecycle/MFA、真实 PostgreSQL RLS 运行证明、React package build/browser E2E、安全对象存储、完整纤芯/熔接模型、2D 编辑器、CSV/XLSX dry-run 导入、NetBox/Webhook、离线 PWA、负载验证、备份恢复和 Kubernetes 生产部署。
