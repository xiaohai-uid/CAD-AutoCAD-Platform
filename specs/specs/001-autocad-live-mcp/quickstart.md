---
title: "Quickstart: AutoCAD MCP v1 端到端验证指南"
description: 六个验证场景对照规格成功标准 SC-1 至 SC-6：环境前置、服务独立冒烟、单实体落图计时、五图元批量与逐项报告、错误人话指引、二十步连续操作加中途重启恢复，附撤销精确性与万级分页测法。
date: 2026-08-24
feature: 001-autocad-live-mcp
tags: [quickstart, validation]
---

# Quickstart: 端到端验证指南

> 验收口径对应 [[001-autocad-live-mcp-spec|spec.md]] Success Criteria；契约细节见 [[001-autocad-live-mcp-contracts|contracts/mcp-tools.md]]。

## 前置条件

1. Windows 侧：AutoCAD 2026 已启动并新建一张空白图纸（Drawing1）
2. Windows Python 3.12 已安装依赖：`pip install mcp pywin32`
3. WSL 侧：DSH 会话可执行 `/mnt/c/.../python.exe`

## 场景 0 — 服务自检（不依赖 AutoCAD）

```bash
/mnt/c/Windows/System32/cmd.exe /c "python -m cad_mcp.smoke --selfcheck"
```
预期：打印依赖版本与模块导入 OK，退出码 0。失败则先修环境再继续。

## 场景 1 — 单实体落图（SC-1 ≤10s）

对已注册的 agent 说："在 (0,0) 到 (100,0) 画一条直线"。
预期：AutoCAD 画布出现直线；agent 返回 `ok=true` + 句柄；**秒表 ≤10s**（AutoCAD 已启动为前提）。

## 场景 2 — 批量落图 + 尽力而为（SC-2 / Q2 决议）

指令（含 5 图元）："画一个左下角 (0,0)、100×50 的矩形；在 (50,25) 画半径 10 的圆；写文字'法兰盘'在 (50,60)"。
预期：矩形/圆/文字全部出现（矩形=1 条多段线）；返回句柄数与画布一致率 100%；随后追加一条非法指令（如半径 -5 的圆）→ 返回 INVALID_PARAM 且指明参数。

## 场景 3 — 错误场景人话化（SC-3）

依次：关闭 AutoCAD → 调用 cad_status → 预期 NOT_RUNNING + 启动指引（≤3s 返回，无挂起）；重开 AutoCAD → 再调任意工具 → 惰性重连成功继续（Q4 决议）。

## 场景 4 — 连续操作 + 中途重启（SC-4）

脚本化连续 20 步混合操作（画/查/图层），全程零失败；第 10 步后手动重启 AutoCAD，第 11 步起自动恢复。

## 场景 5 — 撤销精确性（SC-5 / Q1 单步语义)

画三个实体（三次调用）→ undo 一次 → 仅第三次调用的产物消失，前两次保留 → 再 undo 提示"无可撤销操作"；期间手动画的实体永不被撤掉。

## 场景 6 — 万级分页（SC-6）

用脚本生成 10000 个小圆 → cad_query_entities 首页计时 ≤2s，跳到第 100 页 ≤5s，total=10000 准确。

## 通过标准

场景 0–6 全部符合预期 = v1 验收通过。任一场景失败：修复后**全量重跑**，不允许只补跑失败项。
