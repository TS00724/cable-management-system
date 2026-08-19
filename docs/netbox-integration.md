# NetBox 集成决策

选择主文档建议的 **Option B：独立领域模型 + NetBox adapter**。

## 原因

本产品的强 SaaS 租户边界、跨组织承包商授权、施工审批、路径坐标、标准策略和 3D 空间模型不是 NetBox 的天然授权/工作流边界。把 NetBox 作为内部主数据会增加隔离和扩展耦合。

## 目标接口

```text
InfrastructureAdapter
├── NetBoxAdapter
├── CSVAdapter
└── FutureDCIMAdapter
```

适配流程必须包含：

`read → normalize → map → validate → dry-run → conflict report → commit`

## 候选映射

- Site/Location → Location
- Rack → Rack
- DeviceType/Device → DeviceTemplate/Device
- Interface/FrontPort/RearPort → Port/PortMapping
- Cable/Termination → Cable/CableTermination
- Tenant（可选）→ Organization metadata

## 当前状态

仅完成架构与映射设计；尚未实现 NetBox API 客户端、凭据保管、增量同步、冲突解决和回写。
