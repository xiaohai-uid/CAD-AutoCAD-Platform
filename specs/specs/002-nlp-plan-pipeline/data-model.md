---
title: "Data Model: v3 Plan 流水线"
description: Plan 计划数据模型七字段（layers/entities/dimensions/texts/assumptions/warnings/unit）、ValidationIssue 结构、ParseResult 结构，及 parse→validate→execute 的状态流转定义。
date: 2026-08-24
feature: 002-nlp-plan-pipeline
tags: [data-model]
---

# Data Model: v3

> 继承前作 CADPlanEngine 模型；契约见 [[002-nlp-plan-pipeline-contracts|contracts/mcp-tools.md]]。

## ParseResult（cad_parse_text 输出）
`{intent:"create"|"edit"|"unknown", entities:[{kind,params…}], unit, missing:[str], text}`

## Plan（一等公民纯数据）
| 字段 | 类型 | 说明 |
|------|------|------|
| layers | [{name,color?,linetype?}] | 计划用层 |
| entities | [{id?,kind,params,layer?}] | kind ∈ v1 六类 |
| dimensions | [{type:aligned\|linear\|diameter\|radius, params}] | 真 DIMENSION 定义 |
| texts | [{text,x,y,height?,layer?}] | |
| assumptions | [{field,value,reason}] | 解析时填入的默认假设 |
| warnings | [str] | 非阻断提示 |
| unit | "mm"(默认) | |
| output_level | "sketch"\|"professional" | |

状态流：`parse→Plan→validate→(issues≤warning)→execute→OperationResult(透传 assumptions/warnings)`。

## ValidationIssue
`{severity:"error"|"warning", category:"completeness"|"consistency"|"executability"|"professional", code, message, location?}`
execute 仅在存在 severity=error 时拒绝。
