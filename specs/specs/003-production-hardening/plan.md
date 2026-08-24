---
title: "Plan: 生产加固 P0"
description: 会话层改造三件（可疑态/泄漏上限/write_safe 语义）+ 冒烟套件模块 + CI 工作流；全部调用点按读写分类更新，测试先行覆盖假 App 断连注入场景。
date: 2026-08-24
feature: 003-production-hardening
tags: [plan]
---

# Plan: 生产加固 P0

| 项 | 方案 |
|----|------|
| 可疑态 | `_suspect` 标记 + `_leaked` 计数（上限5）；execute 入口预检 |
| 防重放 | `execute(fn, write_safe=True)` 默认不重放；仅 status/query/list/get 显式传 False |
| 冒烟套件 | `smoke_suite.py` 复用 MCP 客户端六检查，JSON+表格双输出 |
| CI | `.github/workflows/ci.yml` windows-latest + pytest |

调用点分类：读=status/query_entities/list_layers/list_documents/list_blocks/get_entity/init_sheet(幂等可重放)；写=其余全部。
