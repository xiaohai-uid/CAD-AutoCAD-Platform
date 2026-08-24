---
title: "Feature Specification: NLP 解析与计划流水线 v3"
description: 继承创始人前作 CAD-AutoCAD-Platform 的九引擎思想：确定性中英文尺寸解析、Plan-Validate-Execute 三段式（计划含 assumptions/warnings）、五层制图模板一键初始化、图片转几何、DWG 扫描输入；定义六新工具五条用户故事与可测成功标准。
date: 2026-08-24
feature: 002-nlp-plan-pipeline
tags: [spec, nlp, plan, pipeline]
---

# Feature Specification: NLP 解析与计划流水线 v3

> 思想来源：创始人前作 [CAD-AutoCAD-Platform](https://github.com/xiaohai-uid/CAD-AutoCAD-Platform)（九引擎微服务）→ 本特性以 MCP 单进程形态继承其 Intake/CADPlan/Validation/DWG-Scan/Vision 五引擎精髓。治理原则见 [[001-autocad-live-mcp-spec|v1 规格]] 与项目宪法。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 确定性文本解析兜底 (Priority: P1)

作为 agent，当我对用户话语中的尺寸拿不准时，调用 `cad_parse_text("画一个Φ30的圆和200x100的矩形，45°斜线")`，得到结构化结果：`{entities:[{kind:circle,diameter:30},{kind:rectangle,width:200,height:100},{kind:line,angle:45}], unit:"mm", intent:"create", missing:[...]}`——正则确定性提取，零幻觉。

**Acceptance Scenarios**:
1. 中英文混合句（"draw a Φ30 圆 and 100x50 rect"）→ 全部实体被捕获且数值精确
2. 无任何尺寸的话语 → 返回 `missing:["dimensions"]` 而非编造
3. 单位词（mm/cm/inch）出现在文中时被识别进 `unit`

### User Story 2 - 计划一等公民：先规划、再校验、后执行 (Priority: P1)

作为 agent，我可以先调 `cad_plan(text)` 生成结构化图纸计划 `{layers[], entities[], dimensions[], texts[], assumptions[], warnings[]}`——计划是纯数据不落图；经 `cad_validate_plan(plan)` 四类校验（完整性/一致性/可执行性/专业性）拿到 issue 清单；修正后 `cad_execute_plan(plan)` 一次性落图（整批一个撤销单元）。执行结果与计划逐项对应。

**Acceptance Scenarios**:
1. plan→execute 往返：创建的实体数量/类型与 plan.entities 一一对应
2. 含越界坐标或负半径的计划被校验拦截并给出具体 issue
3. assumptions/warnings 从 plan 透传到 execute 结果中（agent 可见推理依据）
4. 同一 plan 重复执行产生重复图元（幂等性由 agent 负责，工具如实执行）

### User Story 3 - 标准制图环境一键初始化 (Priority: P1)

作为绘图者，调用 `cad_init_sheet(template:"gb-mech", size:"A4", title_block:true)` 一次获得：五层标准图层体系（轮廓线粗/中心线红点划/标注绿/填充灰/文字黄）、图框、简化标题栏。幂等：重复调用不重建已存在图层。

**Acceptance Scenarios**:
1. 新图纸调用后 `cad_list_layers` 出现全部五层且属性正确
2. 重复调用第二次返回 created=false 列表且无副作用

### User Story 4 - 图片转几何 (Priority: P2)

作为 agent，给定一张手绘稿/截图路径，`cad_import_image_geometry(path)` 用 OpenCV 检测直线/圆/矩形（带 confidence），返回可直接喂给 `cad_create_batch` 的 items 数组（含预览缩放参数）。未安装 opencv 时返回明确安装指引而非崩溃。

**Acceptance Scenarios**:
1. 含一个矩形和两个圆的测试图 → 检出 1 rect + 2 circles，confidence ≥0.5
2. 无 opencv 环境 → 错误码 MISSING_DEP + pip 安装指引

### User Story 5 - DWG 扫描输入 (Priority: P2)

作为 agent，`cad_scan_dwg(path)` 打开目标 DWG（COM 打开后枚举），返回 `{entities 按类型计数, layers[], sample[] 前 N 个实体摘要}` 并关闭文档不留标签。

**Acceptance Scenarios**:
1. 对本机已知 DWG 扫描 → 实体计数与手工打开核对一致
2. 文件不存在 → NOT_RUNNING 类人话错误（FILE_NOT_FOUND）

## Requirements *(mandatory)*

### Functional Requirements
- **FR-8 解析器**：正则库覆盖 WxH 矩形、Φ直径、R半径、"半径R"、"直径"、角度°、单位词、意图词(画/create/edit)；中英文等价；解析失败如实报告缺失项
- **FR-9 计划模型**：Plan 为纯数据（JSON 可序列化），字段 layers/entities/dimensions/texts/assumptions/warnings/unit/output_level
- **FR-10 四类校验**：completeness(必填缺失)/consistency(引用一致/坐标互斥)/executability(参数合法/边界内)/professional(图层规范建议)，issue 带 severity 与位置
- **FR-11 计划执行**：复用 create_batch 通道；dimensions 用真 DIMENSION 对象；整批一个撤销单元；透传 assumptions/warnings
- **FR-12 制图模板**：gb-mech 五层（颜色/线型对齐 v1 已有约定），可选 A4 图框+标题栏；幂等
- **FR-13 图片几何**：OpenCV Hough/轮廓检测 line/circle/rect + confidence；依赖缺失优雅降级
- **FR-14 DWG 扫描**：COM 打开外部文件枚举统计后关闭；不污染当前会话文档列表超过必要时间

- **FR-15 行业规则包**：`cad_validate_plan(plan, ruleset)` 支持外置 JSON 规则包（内置 mechanical-gb / architectural-gb-seed / chemical-pid-seed 三包）；`cad_list_rulesets` 列出可用包；规则引擎按 check 名分派，社区可加包文件扩展——这是"AI 测评设计规范"愿景的执行末端

**非目标（本特性排除）**：PDF 输入解析；复杂 NLU 意图理解（LLM 职责）；gateway 微服务化（保持单进程函数编排）；自动执行 plan 中 dimensions 以外的编辑类操作。

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-7**: 黄金语句集（≥10 条中英文混合）解析准确率 100%（数值级比对）
- **SC-8**: plan→validate→execute 链路端到端 ≤5s（≤30 实体计划）
- **SC-9**: 校验器对注入的 5 类坏计划全部拦截（0 漏报），好计划误报 0
- **SC-10**: init_sheet 在空白图与已有图上行为均正确（新建/跳过判定 100%）
- **SC-11**: 测试图 fixture 的图形检出召回率 ≥90%，误检 ≤1

## Assumptions
- 解析正则移植自创始人前作 intake/cadplan 引擎（MIT 许可，自有版权）
- OpenCV 为可选依赖（extras: `[image]`），核心功能零新增硬依赖
- 扫描 DWG 通过 COM Documents.Open 实现，扫描完即 Close(false)
