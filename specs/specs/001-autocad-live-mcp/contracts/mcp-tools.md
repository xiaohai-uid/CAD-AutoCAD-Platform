---
title: "Contract: MCP 工具契约（一级冻结）"
description: AutoCAD MCP v1 全部 12 个工具的输入输出 schema 冻结：状态、六类绘图、图层两组、分页查询、单步撤销、安全保存，含统一错误码表与批量尽力而为语义，宪法 I 契约先行的落点。
date: 2026-08-24
feature: 001-autocad-live-mcp
tags: [contract, mcp, api]
---

# Contract: MCP 工具契约 v1（宪法 I · 一级冻结）

> 本文件是本项目的一级契约：实现前冻结，变更须同步修订 [[001-autocad-live-mcp-spec|spec.md]]。数据形态定义见 [[001-autocad-live-mcp-data-model|data-model.md]]。

## 公共约定

- 成功：`{ ok: true, message: str, handles?: str[], items?, data? }`
- 失败：`{ ok: false, error: { code, message, hint } }`，错误码：NOT_RUNNING / NO_DOCUMENT / INVALID_PARAM / BUSY_MODAL / SAVE_CONFLICT / PARTIAL / COM_FAILURE
- 坐标一律世界坐标系二维 `[x, y]`，浮点；角度为度（0°=X 正向，逆时针）
- 一次工具调用 = 一个可撤销单元

## 工具清单（12）

### cad_status
查询连接与文档状态。**输入**: `{}`。**输出**: `{ attached: bool, doc_name: str|null, entity_count: int|null }`

### cad_draw_line
**输入**: `{ x1: f, y1: f, x2: f, y2: f, layer?: str }`
校验: 两端点不得重合（INVALID_PARAM）

### cad_draw_circle
**输入**: `{ cx: f, cy: f, r: f, layer?: str }`
校验: `r > 0`

### cad_draw_arc
**输入**: `{ cx: f, cy: f, r: f, start_angle: f, end_angle: f, layer?: str }`
校验: `r > 0`；角度差按逆时针从 start 到 end

### cad_draw_polyline
**输入**: `{ points: [[f,f], …], closed?: bool = false, layer?: str }`
校验: ≥2 个点（closed 时 ≥3）；无连续重复点

### cad_draw_rectangle
**输入**: `{ x: f, y: f, w: f, h: f, layer?: str }`
语义: 左下角 (x,y)，单条 LWPOLYLINE 实体（一个句柄）。校验: `w > 0, h > 0`

### cad_draw_text
**输入**: `{ text: str, x: f, y: f, height?: f = 3.5, layer?: str }`
默认: 字高 3.5mm + MCP_CN 样式（D5，中文兼容），显式传参覆盖。校验: text 非空；height > 0

### cad_create_layer
**输入**: `{ name: str, color?: int, linetype?: str }`
幂等：已存在同名层直接返回其信息（ok=true, created=false）。linetype 未加载时自动尝试加载，失败报 INVALID_PARAM

### cad_list_layers
**输入**: `{}`。**输出**: `{ layers: [{ name, color, linetype, on }] }`

### cad_query_entities
**输入**: `{ page?: int = 1, page_size?: int = 100 }`
校验: `page ≥ 1, 1 ≤ page_size ≤ 500`
**输出**: `{ total: int, page: int, page_size: int, items: [{ handle, type, layer, geometry }] }`——geometry 按 GeometrySummary 类型化；性能目标 SC-6（首页 ≤2s，任意页 ≤5s）

### cad_undo
**输入**: `{}`。**输出**: `{ removed_handles: str[], skipped_handles: str[] }`
无日志可撤时 ok=true 且两数组皆空、message="无可撤销操作"

### cad_save_dwg
**输入**: `{ path: str, overwrite?: bool = false }`
目标已存在且 overwrite≠true → SAVE_CONFLICT。成功输出 `{ saved_path }`

### cad_create_batch　*（修订 v1.1，2026-08-24）*
> 修订原因：落实 clarify Q2 决议的载体——单类型工具不存在部分失败；且一次指令聚合为一次调用后，"一次工具调用=一个可撤销单元"同时精确满足 Q1。

**输入**: `{ items: [{ kind: "line"|"circle"|"arc"|"polyline"|"rectangle"|"text", …同各单体工具参数 }] }`
校验: items 非空、≤200 个；逐项参数校验。
**语义**: 尽力而为（Q2）——逐项尝试，互不影响；全部成功时 ok=true；任一失败 ok=false+code=PARTIAL，items 逐项给出 `{ index, ok, handle?, error_code?, reason? }`；已创建句柄计入撤销日志（整批=一个撤销单元）。
**输出**: `{ created: int, failed: int, handles: [...], items: [...] }`

## 工具总数：13

## 并发与超时

- 服务单线程串行处理调用（MCP stdio 天然逐请求）
- 所有 COM 调用受 15s 看门狗保护（D6），超时 → BUSY_MODAL

---

# Contract v2.0 增补（2026-08-24，创始人指令：功能对齐并超越竞品）

> 设计原则：AI 是主要用户。新增 20 个工具（总数 13→33）。分组见下；错误码沿用公共约定。
> （勘误 2026-08-24：原文误记 +21/34，实为 +20/33。）

## 尺寸标注（真 DIMENSION 对象）
### cad_dim_aligned
`{x1,y1,x2,y2, ox,oy, text?}` 两界址点+尺寸线偏移点；输出 `{handle}`
### cad_dim_diameter
`{handle, chord_x, chord_y, leader_len?=5, text?}` 圆/弧直径标注
### cad_dim_radius
`{handle, chord_x, chord_y, leader_len?=5, text?}`

## 填充与多行文本
### cad_hatch
`{pattern?="ANSI31", handles:[…闭合实体句柄], scale?=1, angle_deg?=0, layer?}` → 关联填充
### cad_draw_mtext
`{text, x, y, width, height?=3.5, layer?}`

## 逃生舱（兜底一切）
### cad_send_command
`{command}` 向命令行发送任意命令/AutoLISP（如 "(setq a 1)"）。**fire-and-forget**：无返回值，结果需经 cad_status/cad_query_entities 观察。

## 实体操作
### cad_get_entity
`{handle}` → `{type,layer,geometry}`（复用 GeometrySummary）
### cad_delete_entities
`{handles:[…]}` → `{removed,skipped}`；若句柄在撤销日志中同步移除

## 图层与文档
### cad_set_layer_props
`{name, color?, linetype?, on?, frozen?, current?}` 至少一个可变字段
### cad_list_documents
`{}` → `{docs:[{name,active}]}`
### cad_activate_document
`{name}`

## 块
### cad_list_blocks → `{blocks:[name]}`
### cad_insert_block
`{name, x, y, scale?=1, rot_deg?=0, layer?}`

## 视觉闭环（★独有）
### cad_zoom
`{mode:"extents"|"window", x1?,y1?,x2?,y2?}`
### cad_export_screenshot
`{path}` 将 AutoCAD 窗口截屏存 PNG，返回 saved_path —— agent 自反馈闭环

## 参数化生成器（★一次调用出整套图元）
### gen_bolt
`{d=12, L=50, std?:"GB/T 5782"}` 六角头螺栓双视图（端口同 _real_drawing 教学版），整批一个撤销单元
### gen_flange
`{D=200, K=160, n=8, L=18, b=20, d1=128, A=89, f?=2, scale=0.5, origin=[x,y]}` 法兰双视图
### gen_gear_spur
`{z=20, module=2, bore_r=10, pressure_angle?=20}` 渐开线齿廓近似折线+内孔
### cad_array_polar
`{handle, count, fill_deg=360, cx, cy}`
### cad_array_rect
`{handle, rows, cols, row_dx, col_dy}`
