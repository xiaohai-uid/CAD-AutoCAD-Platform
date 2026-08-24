---
title: "Data Model: AutoCAD MCP v1"
description: 领域实体定义：活动图纸、图元（句柄/类型/几何摘要）、图层、统一操作结果与错误码、单步撤销操作日志，及各实体的校验规则与状态转换（附着→就绪→操作中→失效重连）。
date: 2026-08-24
feature: 001-autocad-live-mcp
tags: [data-model, design]
---

# Data Model: AutoCAD MCP v1

> 实体来源：[[001-autocad-live-mcp-spec|spec.md]] Key Entities + clarify 决议；契约落地见 [[001-autocad-live-mcp-contracts|contracts/mcp-tools.md]]。

## Entity: DrawingDocument（活动图纸）

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 文档名（如 Drawing1.dwg） |
| is_active | bool | 是否有可用活动文档 |
| entity_count | int | 模型空间实体总数 |

状态转换：`未附着 → 已附着(有文档) → 操作中 → 连接失效 --惰性重连--> 已附着 | 未附着`。无持久化；服务重启即回到未附着。

## Entity: EntityHandle（图元引用）

- `handle: str`——AutoCAD 原生句柄，十六进制字符串，文档内唯一。**规范术语：句柄**。
- 校验规则：撤销时按句柄定位实体，实体已不存在（用户手删）则跳过并在结果中如实列出。

## Entity: GeometrySummary（几何摘要，按类型）

| 类型 | 字段 |
|------|------|
| LINE | start:[x,y], end:[x,y] |
| CIRCLE | center:[x,y], radius |
| ARC | center, radius, start_angle, end_angle |
| LWPOLYLINE | points:[[x,y]…], closed |
| TEXT | position:[x,y], text, height, style |

坐标均为世界坐标系(WCS)二维 XY；v1 不涉及 Z 轴与 UCS 换算。

## Entity: Layer

| 字段 | 类型 | 校验规则 |
|------|------|----------|
| name | str | 非空 ≤255 字符，允许中文 |
| color | int? | ACI 颜色索引 1-255 |
| linetype | str? | 必须已加载（Continuous 默认存在） |

## Entity: OperationResult（统一结果，宪法 IV）

```
{ ok: true,  message: str, handles: [handle…], items?: [per-item…] }   // 成功
{ ok: false, error: { code, message, hint } }                          // 失败
```

错误码体系：

| code | 场景 | hint 示例 |
|------|------|-----------|
| NOT_RUNNING | 无运行实例 | 请启动 AutoCAD 并新建图纸 |
| NO_DOCUMENT | 无活动文档 | 请新建或打开一张图纸 |
| INVALID_PARAM | 参数校验失败 | 指明哪个参数非法及原因 |
| BUSY_MODAL | COM 超时(D6) | 请检查是否有未关闭对话框 |
| SAVE_CONFLICT | 目标文件已存且未确认 | 重试时带 overwrite=true |
| PARTIAL | 批量部分成功(Q2) | 见 items 逐项成败 |
| COM_FAILURE | 其他 COM 异常 | 原始信息 + 建议 |

批量语义（Q2）：`ok` 仅当全部成功为 true；部分失败时 `ok=false, code=PARTIAL`，但**已创建的句柄仍随结果返回**，且记入撤销日志（一次调用 = 一个可撤销单元）。

## Entity: OperationJournal（操作日志，Q1 决议载体）

- 仅保留**最近一次**成功调用的 `{tool, handles[]}`（内存单槽）。
- cad_undo 读取该槽 → 按句柄删除 → 清空槽。连续两次 undo 第二次返回"无可撤销操作"。
- 用户手工绘制不进入日志，故永不被 agent 的 undo 波及。
