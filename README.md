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
- 自动化安全、API、迁移和业务规则测试

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

打开 `http://localhost:8000/app/`；OpenAPI 为 `http://localhost:8000/docs`。

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

## 开发 dry-run 验证

项目当前**禁止使用 GitHub Actions**。开发期间仅保留本地 dry-run 门禁：

```bash
make dry-run
```

该命令运行：

- Pytest 单元、集成和安全测试
- Python 编译检查
- 前端 ES Module / WebGL 语法检查
- 空 SQLite 数据库 Alembic migration
- 同一数据库 seed 连续执行两次的幂等验证

`make verify` 保留为 `make dry-run` 的兼容别名。详细证据见 `docs/DRY_RUN_STATUS.md`。

也可手工从空数据库执行：

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

## 演示身份

`/api/v1/demo/context` 仅在 `DEMO_MODE=true` 时返回演示 UUID。浏览器 UI 使用请求头模拟三种主体：

- Alice Admin：Northstar Tenant Owner
- Tina Technician：Metro 承包商现场技术员，仅限 Engineering Building Upgrade Project
- Sam Supervisor：Northstar Infrastructure Manager

生产环境不能使用演示请求头作为身份凭据；必须完成 OIDC JWT 校验并从受信任令牌建立主体。

## 重要边界

本仓库是经过测试的第一条纵向链路，不是主构建文档全部范围的最终商业版本。尚未完成的重点包括 OIDC 令牌校验、真实 PostgreSQL RLS 运行证明、安全对象存储、完整纤芯/熔接模型、2D 编辑器、导入导出、NetBox/Webhook、离线 PWA、浏览器 E2E、负载验证、备份恢复和 Kubernetes 生产部署。
