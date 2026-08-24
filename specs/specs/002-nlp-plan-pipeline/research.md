---
title: "Research: v3 流水线决策——继承前作九引擎"
description: 五项决策：正则库整段移植自创始人前作 intake/cadplan 引擎；Plan 采用其 dataclass 结构 JSON 化；四类校验类别沿用并映射为 issue severity；OpenCV 可选依赖优雅降级；DWG 扫描走 COM Documents.Open 即开即关，全部含备选与否决理由。
date: 2026-08-24
feature: 002-nlp-plan-pipeline
tags: [research]
---

# Research: v3 决策记录

> 来源：[[002-nlp-plan-pipeline-spec|spec.md]]；蓝本 github.com/xiaohai-uid/CAD-AutoCAD-Platform（创始人自有，MIT）。

## D1 解析器：整段移植前作 IntakeEngine+CADPlanEngine 正则
- **Decision**: WxH/Φ/R/角度/单位/意图 六组正则原样移植并补中文量词变体
- **Rationale**: 自有版权、已在生产语境打磨过中英文样例；LLM 兜底需要确定性组件
- **Alternatives**: 让 LLM 全责解析（否决——数值幻觉风险）；引入 NLU 库（过重）
## D2 Plan 模型：沿用其 dataclass 结构转 JSON Schema
- **Decision**: layers/entities/dimensions/texts/assumptions/warnings/unit/output_level 七字段
- **Rationale**: assumptions/warnings 字段是亮点（推理透明），必须保留
- **Alternatives**: 自创极简模型（丢掉透明性，否决）
## D3 校验四类沿用，输出统一 issue{severity,code,message,location}
- **Decision**: completeness/consistency/executability/professional 四类；severity=error 才阻断 execute
- **Rationale**: 与前作对齐便于心智迁移；error/warning 两级足够
## D4 OpenCV 可选依赖
- **Decision**: `pip install cad-mcp[image]` extras；缺失返回 MISSING_DEP+指引
- **Rationale**: 核心用户未必需要视觉输入；不拖累零依赖安装
## D5 DWG 扫描即开即关
- **Decision**: Documents.Open(path) → 枚举 ModelSpace 计数+抽样 → Close(False)
- **Rationale**: 不留标签污染会话（对比 v2 踩过的 PATH_IN_USE 坑）
