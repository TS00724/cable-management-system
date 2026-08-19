# ADR-005：关系型物理图

- **状态**：Accepted
- **决策**：Port、CableTermination、PortMapping 和 route junction table 存于 PostgreSQL，服务层构图遍历。
- **理由**：保证事务、唯一约束和审计；当前规模无证据需要图数据库。
- **后果**：深层 fiber 节点通过显式实体扩展；性能数据出现后再评估图投影/缓存。
