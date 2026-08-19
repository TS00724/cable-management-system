# ADR-006：浏览器 WebGL，可迁移至 Three.js/R3F

- **状态**：Accepted for vertical slice
- **决策**：首条链路使用无依赖原生 WebGL验证数据驱动几何。
- **理由**：仓库为空且构建环境受限，可先证明持久化实体到几何的映射。
- **后果**：完整编辑器阶段评估 Three.js/React Three Fiber、GLTF 和实例化。
