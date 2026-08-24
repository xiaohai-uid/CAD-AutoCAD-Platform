---
title: "Research: AutoCAD MCP v1 技术选型"
description: 八项技术决策记录：COM GetActiveObject 附着、Windows Python 直跑零 env 依赖、官方 mcp SDK、按句柄删除实现单步撤销、独立中文大字体样式、模态对话框超时保护、stderr 日志、轻量属性分页策略，均含备选与否决理由。
date: 2026-08-24
feature: 001-autocad-live-mcp
tags: [research, decisions]
---

# Research: AutoCAD MCP v1 技术选型

> 对应规格 [[001-autocad-live-mcp-spec|spec.md]] 的 Assumptions 与 clarify 决议；调研基线为 GitHub 现有方案（daobataotie/CAD-MCP、U-C4N/Autocad-MCP、puran-water/autocad-mcp）。

## D1 附着机制：pywin32 `GetActiveObject("AutoCAD.Application")`

- **Decision**: 用 `win32com.client.GetActiveObject` 取运行中实例（通用 ProgID 自动解析到最新安装版本），失败即报 NOT_RUNNING。
- **Rationale**: 完整版 AutoCAD 注册为本地 COM 服务器，这是官方自动化正道；GitHub 各方案中星数最高的两条路线（daobataotie 512★、Easy-MCP 249★）同款。
- **Alternatives considered**: comtypes 直连（等价，pywin32 更普及）；puran-water 的 LISP+PostMessageW 键击注入（为无 COM 的 LT 设计的 hack，脆弱且我们不需要）；ezdxf 离线生成（v1 非目标）。启动型 `Dispatch` 会新开 AutoCAD 进程，违背"附着已运行实例"的用户拍板，仅作 NOT_RUNNING 错误提示中的建议项。

## D2 进程宿主：Windows python.exe 直跑 + 零环境变量

- **Decision**: 服务以 Windows Python 运行，DSH 经互操作拉起；**服务内部不读取任何环境变量**（ProgID、默认字高等全部内置常量），stdio 跨边界。
- **Rationale**: 实测 WSL→Windows exe 默认不透传环境变量（2026-08-24 FOO 实验，见 [[2026-08-24 OpenDesign daemon 接入 agent 的两条路径与 WSL 关键机制]]）；codex.exe 先例证明 /mnt/c 路径直拉 Windows 可执行文件走 stdio 可行。零 env = 把边界风险降为零。
- **Alternatives considered**: WSLENV 包装脚本（OpenDesign daemon 在用，可行但多一层）；WSL 内跑服务+远程 COM（不可行，COM 不能跨机）。

## D3 MCP 框架：官方 `mcp` Python SDK（FastMCP）

- **Decision**: FastMCP 声明式注册工具函数，stdio transport。
- **Rationale**: 官方维护、协议合规、声明式最薄。
- **Alternatives considered**: 手写 JSON-RPC 框架——违反全局原则"优先成熟库"。

## D4 单步撤销实现：操作日志 + 按句柄删除

- **Decision**: journal.py 记录最近一次成功工具调用创建的全部实体句柄；cad_undo 按句柄逐一删除（句柄已不存在则跳过并如实报告）。
- **Rationale**: 精确落实 Q1 决议"只撤 agent 自己的操作"——原生 Undo 会波及用户手工绘制；句柄删除幂等且可测。
- **Alternatives considered**: AutoCAD `Undo` 命令 + UndoMark（波及用户历史，违反 Q1 决议，否决）。

## D5 中文渲染保障：独立样式 MCP_CN

- **Decision**: 首次需要写文字/建图层时确保存在名为 `MCP_CN` 的文字样式（gbenor.shx + 大字体 gbcbig.shx），不存在则创建；文字默认用此样式。不改用户的 Standard 样式。
- **Rationale**: 简体中文版默认 Standard 常缺大字体映射，汉字渲染成问号是 Q5 风险点；独立样式零侵入。
- **Alternatives considered**: 直接改 Standard（侵入用户配置，否决）。

## D6 模态对话框阻塞：COM 调用超时保护（Deferred 项落位）

- **Decision**: 所有 COM 调用经统一看门狗包装（默认 15s）；超时返回 BUSY_MODAL 错误码与人话指引"请检查 AutoCAD 是否有未关闭的对话框/命令正在进行"。
- **Rationale**: 模态对话框挂起 COM 是 AutoCAD 自动化第一坑，必须快速失败而非无限等待。

## D7 日志观测：logging → stderr（Deferred 项落位）

- **Decision**: 标准 logging 输出到 stderr；stdout 绝对专用 MCP 协议。
- **Rationale**: stdio 传输下 stdout 污染=协议损坏；stderr 由 DSH 侧进程日志可见。

## D8 万级分页性能策略：轻量枚举 + 当前页深读

- **Decision**: 分页枚举只读轻量属性（ObjectName/Handle/Layer）定位窗口，几何参数仅对当前页实体深读；先直测 SC-6，不达标再优化批量读。
- **Rationale**: COM 往返是主要成本；万级全量深读必然爆 SC-6 的 5 秒线。
