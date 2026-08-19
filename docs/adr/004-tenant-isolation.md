# ADR-004：应用保护 + PostgreSQL Forced RLS

- **状态**：Accepted
- **决策**：ORM 查询过滤、写入 guard、tenant-scoped constraints 与 forced RLS 叠加。
- **理由**：任何单层过滤都不足以作为 SaaS 数据边界。
- **后果**：平台操作必须使用独立 BYPASSRLS 角色；真实 PostgreSQL 测试是发布门禁。
