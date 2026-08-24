---
title: "Feature Specification: P1 可观测性·安全边界·浸泡测试"
description: 审计 P1 三项落地：JSONL 轮转结构化日志与工具级耗时追踪、只读模式与安全边界文档化（send_command 风险明示）、浸泡测试框架含 GDI/内存采样并当场短程实测；兼容性矩阵文档化为待环境项。
date: 2026-08-24
feature: 004-p1-observability-security-soak
tags: [spec, observability, security, soak]
---

# Feature Specification: P1 三项

## US1 结构化可观测 (P1)
每工具调用记录：工具名/耗时ms/ok/错误码，双通道——stderr 人话行 + `%TEMP%/cad-mcp/cad-mcp.jsonl` 轮转文件（5MB×3）供机器分析；`--verbose` 开 DEBUG。
验收：任一工具调用后 jsonl 追加一行且字段齐全。

## US2 只读模式与安全声明 (P1)
服务支持 `--read-only` 启动参数：变更类工具一律返回 READ_ONLY 错误（零 env 约束不变，用 argv）；`SECURITY.md` 明示：send_command=任意命令执行、save 无路径白名单、单用户本机假设、MCP 无鉴权。
验收：--read-only 下 draw/save/send_command 全部被拒，查询类正常。

## US3 浸泡测试框架 + 短程实测 (P1)
`soak_test.py --iterations N`：混合操作循环（绘制/查询/撤销/截图抽样），逐轮采样自身进程 WorkingSet 与 AutoCAD 进程 WorkingSet+GDI 句柄数，产出统计报告（p50/p95 延迟、内存/GDI 首末差、错误数）。本机先跑 120 轮短程；8h 全量留档说明。

## Requirements
- FR-17 日志双通道+轮转；工具级追踪字段固定 schema
- FR-18 READ_ONLY_TOOLS 清单驱动只读模式（tools_meta.py 可测纯函数）
- FR-19 浸泡指标采集（ctypes psapi/GetGuiResources，零新增依赖）
## Success Criteria
- SC-16 jsonl 字段完整率 100%（抽查）
- SC-17 --read-only 下变更类 100% 拒绝且查询类 100% 正常
- SC-18 120 轮浸泡：错误 0、GDI 变化 ≤±10、WorkingSet 增幅 ≤25%
