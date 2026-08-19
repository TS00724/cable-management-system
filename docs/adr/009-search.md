# ADR-009：PostgreSQL 搜索起步

- **状态**：Accepted for initial release
- **决策**：租户过滤后的标识符优先 SQL 搜索。
- **理由**：先保证隔离与精确 ID 排序，再用真实规模决定专用索引。
- **后果**：百万级模糊搜索前需 GIN/trigram 或外部索引，并复制同等租户边界。
