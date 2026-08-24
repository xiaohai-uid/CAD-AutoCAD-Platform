---
title: "Feature Specification: 生产加固 P0"
description: 审计四道坎闭环：看门狗超时线程泄漏治理（可疑态+预检+泄漏上限）、写操作防重放（连接死亡快速失败不重试）、无人值守冒烟套件（退出码化可挂计划任务）、GitHub Actions 单测 CI；四项全部可自动化验证。
date: 2026-08-24
feature: 003-production-hardening
tags: [spec, production, hardening]
---

# Feature Specification: 生产加固 P0

> 来源：[[001-autocad-live-mcp-production|PRODUCTION_READINESS.md]] P0 四项。宪法原则 III/IV 延伸：可靠性缺陷按正确性缺陷对待。

## User Stories & Acceptance

### US1 写操作防重放 (P0)
连接中断时，**变更类操作绝不自动重放**：快速失败并提示人工核对；查询类操作保留一次自动重试。
1. Given 写任务中途断连 When 异常上抛 Then 返回 COM_FAILURE 且消息含"未自动重试"，图元无重复
2. Given 查询时连接失效 When 下次调用 Then 惰性重连后正常返回（既有行为保持）

### US2 超时不堆积 (P0)
模态对话框导致连续超时时，服务进入可疑态：后续调用做轻量预检，预检不过直接快速拒绝；泄漏线程计数达上限（5）后持续拒绝并建议重启 AutoCAD。恢复附着即清零。

### US3 无人值守冒烟套件 (P0)
`python -m cad_mcp.smoke_suite` 一条命令跑六项真机检查（自检/附着/绘制撤销往返/批量计数差/初始化幂等/截图导出），输出 PASS/FAIL 表，任一失败退出码非零——可直接挂 Windows 计划任务每日自检。

### US4 CI 单测流水线 (P0)
push/PR 自动在 windows-latest 跑全部纯逻辑测试（无需 AutoCAD）；COM 相关测试打标隔离。

## Requirements
- FR-16 会话可疑态与泄漏上限（默认 5）
- FR-17 execute(fn, write_safe) 语义：默认 True 不重放；读操作显式 False
- FR-18 smoke_suite 六检查 + 非零退出码
- FR-19 ci.yml（windows-latest, Python 3.12）

## Success Criteria
- SC-12 连续 10 次强制超时后服务仍能快速拒绝（<100ms）而非堆积卡死
- SC-13 断连注入下写操作零重复图元（假 App 测试证明）
- SC-14 smoke_suite 在健康环境全 PASS 且 exit=0；拔掉 AutoCAD 后 exit≠0
- SC-15 CI 绿灯
