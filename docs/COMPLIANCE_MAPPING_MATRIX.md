# Compliance Mapping Matrix

本矩阵保留产品控制与未来合法标准条款之间的映射位置。`Clause` 列故意不填，不能在没有授权文本时虚构。

| Control ID | Product control | Implemented evidence | Clause | Mapping status |
|---|---|---|---|---|
| SIM-ID-001 | 租户内基础设施标识唯一 | 唯一约束、标识符服务、重复检查 | TBD | Product control complete; clause pending licensed review |
| SIM-ID-002 | 标识格式由活动 profile 定义 | `identifier_templates`, regex rule | TBD | Configurable |
| SIM-REC-001 | 线缆记录包含两个物理终端 | `CableTermination`, trace validation | TBD | Implemented |
| SIM-REC-002 | 安装和测试状态可审计 | workflow + `AuditEvent` | TBD | Implemented |
| SIM-LBL-001 | 人可读标识与 QR 关联记录 | `LabelService` and QR SVG | TBD | Implemented |
| SIM-LOC-001 | Campus/Building/TR/Rack 层级记录 | typed nested `Location` | TBD | Implemented |
| SIM-PATH-001 | 线缆路径和有序路径段记录 | `CableRouteSegment` | TBD | Implemented |
| SIM-COMP-001 | 缺失、重复、异常和未验证发现 | `ComplianceService` | TBD | Partial rule library |
| SIM-HIST-001 | 标识与拓扑变更历史 | immutable audit | TBD | Partial; full temporal topology pending |
