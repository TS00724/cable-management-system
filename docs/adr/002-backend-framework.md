# ADR-002：FastAPI + SQLAlchemy + Alembic

- **状态**：Accepted
- **决策**：Python 3.12+ 模块化单体。
- **理由**：类型化 OpenAPI、成熟 ORM/迁移、易于表达事务和图遍历。
- **后果**：通过模块服务和测试约束耦合；不为“企业感”提前拆微服务。
