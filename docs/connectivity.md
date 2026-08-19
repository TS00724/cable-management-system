# 物理连通图

## 表示

- `Port`：一等物理连接点
- `CableTermination`：线缆一端对一个端口的占用
- `PortMapping`：设备内部的前后端、lane 或 cassette 映射
- `CableRouteSegment`：线缆对有序路径段的引用

```mermaid
flowchart LR
    SW[Switch G01] --> PC[Patch cord]
    PC --> PPF[Patch panel F01]
    PPF --> MAP[front_rear mapping]
    MAP --> PPR[Patch panel R01]
    PPR --> HC[Horizontal Cat6A cable]
    HC --> WA[WA-2-101-A Port A]
```

## 追踪算法

1. 从所选线缆的两个终端端口开始。
2. 分批查询这些端口关联的线缆终端和内部映射。
3. 建立无向邻接表并递归扩展。
4. 设定 500 节点安全上限，防止未记录环路导致无界遍历。
5. 选择包含目标线缆的最长物理路径。
6. 对路径中的每条线缆附加有序 pathway segment 和坐标。

示范链路经自动验证为：

`port → cable → port → internal_mapping → port → cable → port`

## 物理校验

- 同一端口不能有两个物理终端
- A/B 端不能是同一端口
- 线缆和端口介质族必须兼容
- 线缆必须有恰好两个终端才能追踪
- 路径段必须属于当前租户并真实存在

## 后续

完整 fiber lane、strand/pair、splice、splitter、breakout 和多分支回路需要扩展图节点类型，不应退化成 A/B 字符串。
