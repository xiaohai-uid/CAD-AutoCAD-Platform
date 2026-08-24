---
title: "Implementation Plan: AutoCAD 实时操控 MCP v1"
description: 技术方案：Python 3.12 + mcp(FastMCP) + pywin32 COM 附着已运行 AutoCAD 2026；12 工具契约、单步撤销操作日志、中文样式保障、惰性重连与分页查询的实现选型，含宪法合规检查表。
date: 2026-08-24
feature: 001-autocad-live-mcp
tags: [plan, speckit, mcp, autocad]
---

# Implementation Plan: AutoCAD 实时操控 MCP v1

**Branch**: `001-autocad-live-mcp` | **Date**: 2026-08-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-autocad-live-mcp/spec.md`

> 选型依据见 [[001-autocad-live-mcp-research|research.md]]；开发顺序遵循 [[2026-08-24 决策 项目开发顺序约定——契约先行+不确定性排序+双分支即规格完善]]。

## Summary

构建一个 MCP stdio 服务，让 DSH agent 通过 12 个结构化工具实时附着并操控用户打开的 AutoCAD 2026（简体中文版）：六类图元绘制、图层管理、分页查询、单步撤销、安全保存。技术路线：Windows Python 3.12 进程内运行官方 mcp SDK（FastMCP），经 pywin32 COM `GetActiveObject` 附着已运行的 AutoCAD 实例；服务零环境变量依赖以规避 WSL→Windows 边界的 env 不透传问题。

## Technical Context

**Language/Version**: Python 3.12.10（Windows 宿主侧，已装于 C:\Users\a1691）
**Primary Dependencies**: `mcp`（官方 Python SDK，FastMCP server）· `pywin32`（COM 自动化）
**Storage**: N/A——无持久化；仅内存保留最近一次操作的句柄日志（供撤销）
**Testing**: pytest（领域逻辑 TDD）+ 真机冒烟脚本（COM 集成验收关卡）
**Target Platform**: Windows 10/11 + AutoCAD 2026 简体中文完整版；服务进程由 WSL 内 DSH 经互操作拉起
**Project Type**: stdio 服务（MCP server）
**Performance Goals**: 单图元指令到画布可见 ≤10s；万级实体查询首页 ≤2s、任意页 ≤5s
**Constraints**: stdout 专用于 MCP 协议（日志走 stderr）；不依赖任何跨 WSL 边界传递的环境变量；模态对话框阻塞时快速失败不得挂起
**Scale/Scope**: 单用户本机；12 个工具；预计 ≤1500 行

## Constitution Check

| 原则 | 状态 | 依据 |
|------|------|------|
| I. 契约先行 | ✅ PASS | contracts/mcp-tools.md 先于任何实现代码产出并冻结 |
| II. 最小端到端 | ✅ PASS | 仅 live 单后端；未为 ezdxf/3D 预埋任何抽象 |
| III. 测试优先 | ✅ PASS | 领域逻辑（参数校验/结果组装/分页切片）TDD；真机冒烟作为集成关卡列入任务 |
| IV. 结构化结果 | ✅ PASS | 统一 OperationResult 形态 + 错误码体系（见契约） |
| V. 简洁 | ✅ PASS | 无 speculative 配置项；模块单一职责 |

**Gate 结论**: 无违规，进入 Phase 0。

## Project Structure

### Documentation (this feature)

```
specs/001-autocad-live-mcp/
├── spec.md              # 规格基线（含 5 条澄清决议）
├── plan.md              # 本文件
├── research.md          # Phase 0: 技术选型决策记录
├── data-model.md        # Phase 1: 领域实体与状态
├── quickstart.md        # Phase 1: 端到端验证指南
└── contracts/
    └── mcp-tools.md     # 一级契约：12 个工具的输入/输出 schema
```

### Source Code (repository root)

```
autocad-mcp/
├── src/cad_mcp/
│   ├── server.py        # FastMCP 装配 + 12 工具注册（薄层）
│   ├── session.py       # 连接会话：附着/惰性重连/文档状态
│   ├── drawing.py       # 六类图元创建（领域逻辑，可离线测参数校验）
│   ├── layers.py        # 图层创建/列举 + 中文样式保障
│   ├── query.py         # 分页枚举与几何摘要
│   ├── journal.py       # 操作日志：最近一次句柄集（撤销依据）
│   ├── result.py        # OperationResult 构造与错误码体系
│   └── smoke.py         # 真机冒烟脚本（python -m cad_mcp.smoke）
└── tests/               # pytest：result/journal/drawing 校验逻辑
```

**Structure Decision**: 单项目布局（Option 1）。server.py 只做协议装配，全部业务在可离线测试的纯逻辑模块中；smoke.py 是唯一触碰真实 AutoCAD 的入口，对应宪法 III 的验收关卡。

## Complexity Tracking

无不必要复杂度引入。唯一值得记录的权衡：撤销采用"按句柄删除"而非 AutoCAD 原生 Undo 标记（理由见 research.md D4），换来精确的"只撤 agent 自己的操作"语义。
