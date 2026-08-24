---
title: "Tasks: AutoCAD 实时操控 MCP v1"
description: 27 项可执行任务：骨架与依赖、基础模块 TDD、真机垂直冒烟闸门（一条直线落图后才许铺开）、四条用户故事各成独立可测增量、收尾含 DSH 接线部署与 SC-1 至 SC-6 全量回归。
date: 2026-08-24
feature: 001-autocad-live-mcp
tags: [tasks, implementation]
---

# Tasks: AutoCAD 实时操控 MCP v1

**Input**: Design documents from `/specs/001-autocad-live-mcp/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/mcp-tools.md ✅ quickstart.md ✅
**Tests**: 宪法 III 强制领域逻辑 TDD（先红后绿）；COM 集成点以 smoke 真机关卡验收。
> 执行约定遵循 [[2026-08-24 决策 项目开发顺序约定——契约先行+不确定性排序+双分支即规格完善]]：T009 是消除最大不确定性的最早垂直冒烟。

## Phase 1 — Setup

- [x] T001 创建项目骨架：`pyproject.toml`（deps: mcp/pywin32/pytest）+ `src/cad_mcp/__init__.py` + `tests/__init__.py`，目录结构照 plan.md
- [x] T002 Windows Python 安装依赖并自检：`cmd.exe /c "python -m pip install mcp pywin32 pytest"` 后 `python -c "import mcp, win32com.client"` 通过

## Phase 2 — Foundational（阻塞后续全部故事）

- [x] T003 [P] 先写 `tests/test_result.py`（红）：七类错误码构造、成功形态、PARTIAL 批量逐项语义（契约见 contracts/mcp-tools.md 公共约定）
- [x] T004 [P] 实现 `src/cad_mcp/result.py`（绿）：OperationResult 构造器 + 错误码常量 + hint 文案表
- [x] T005 [P] 先写 `tests/test_journal.py`（红）：单槽日志写入/覆盖/清空/连续 undo 第二次为空
- [x] T006 [P] 实现 `src/cad_mcp/journal.py`（绿）：最近一次操作句柄集（Q1 决议载体）
- [x] T007 实现 `src/cad_mcp/session.py`：GetActiveObject 附着（D1）、惰性重连一次（Q4）、15s 看门狗包装器（D6）、文档状态读取
- [x] T008 实现 `src/cad_mcp/smoke.py` 最小冒烟：attach → AddLine(0,0)-(100,0) → 回报句柄（D2 零 env 依赖）
- [x] T009 **真机闸门**：启动 AutoCAD 开新图纸，运行 smoke → 直线出现在画布且句柄返回。**不绿不得进入任何 US 任务**
- [x] T010 [P] 实现 `src/cad_mcp/server.py` FastMCP 骨架 + 注册 cad_status（契约 schema），stdio 启动手动连通自检

## Phase 3 — US1 自然语言绘图落图 (P1)

**Goal**: 六类图元从 agent 指令到画布可见。**Independent Test**: 场景 1+2——单实体 ≤10s；五图元批量逐项报告。

- [x] T011 [P] [US1] 先写 `tests/test_drawing.py`（红）：负半径、重合端点、空文本、height≤0、points<2 等校验用例
- [x] T012 [US1] 实现 `src/cad_mcp/drawing.py` 六类创建函数（含纯校验器）+ ensure_layer/MCP_CN 样式助手（绿）；文字默认 gbenor+gbcbig（D5）
- [x] T012b [US1] 契约 v1.1 落地：drawing.py 增加 batch 分派器（逐项校验+尽力而为），server.py 注册 cad_create_batch
- [x] T013 [US1] `server.py` 注册 cad_draw_line/circle/arc/polyline/rectangle/text 六工具，schema 与契约逐字段一致；批量尽力而为语义接入 PARTIAL
- [x] T014 [US1] 冒烟扩展：场景 1 计时（SC-1）+ 场景 2 五图元一致率与非法参数混入的逐项报告（SC-2）

## Phase 4 — US2 图层管理 (P1)

**Goal**: 图层规范化归属。**Independent Test**: "新建红色虚线 center 层并画中心线"全链路。

- [x] T015 [P] [US2] 先写 `tests/test_layers.py`（红）：同名幂等返回 created=false、未加载 linetype 自动加载、加载失败 INVALID_PARAM
- [x] T016 [US2] 实现 `src/cad_mcp/layers.py`（绿）：create 幂等/list/color+linetype
- [x] T017 [US2] `server.py` 注册 cad_create_layer / cad_list_layers；smoke 补中心线场景

## Phase 5 — US3 查询反馈闭环 (P1)

**Goal**: agent 能读图纸。**Independent Test**: 三已知实体查询一致；万级分页达标。

- [x] T018 [P] [US3] 先写 `tests/test_query.py`（红）：切片边界（首页/末页/越界空页/page_size=500 上限/下限 1）
- [x] T019 [US3] 实现 `src/cad_mcp/query.py`（绿）：轻量枚举定位窗口 + 当前页几何深读（D8）
- [x] T020 [US3] `server.py` 注册 cad_query_entities；脚本生成万级圆 → SC-6 计时（首页≤2s 翻页≤5s），不达标按 D8 迭代

## Phase 6 — US4 安全网 (P2)

**Goal**: 可回退、防覆盖。**Independent Test**: 三实体两连撤精确性 + 覆盖冲突拒绝。

- [x] T021 [US4] 在 `src/cad_mcp/server.py` 实现 cad_undo 工具：读 journal 按句柄删除、消失句柄跳过并如实列入 skipped_handles、清槽
- [x] T022 [P] [US4] 在 `src/cad_mcp/server.py` 实现 cad_save_dwg 工具：存在性检查 → SAVE_CONFLICT / overwrite=true 放行
- [x] T023 [US4] 冒烟场景 5：三实体两次 undo 的精确回退 + 用户手绘图元永不被撤（Q1 决议验证）

## Phase 7 — Polish & Cross-Cutting

- [x] T024 全局审计：全部 COM 调用经看门狗（D6）；日志仅 stderr（D7）；stdout 协议纯净性（污染即协议损坏）
- [x] T025 quickstart 场景 0–6 全量回归；任一失败修复后全量重跑
- [x] T026 部署接线：`~/.dsh/profiles/web/cordis.patch.yml` 新增 `mcp-autocad` 条目（command=/mnt/c Windows python.exe，args=-m cad_mcp.server，零 env），新会话确认 12 工具可见
- [x] T027 终验：SC-1~SC-6 逐条勾稽记录证据（计时截图/输出），更新 checklists/requirements.md 备注

## Dependencies

```
T001→T002→(T003,T005 并行)→(T004,T006)→T007→T008→T009【闸门】→T010
T009 后四条 US 线独立：US1(T011-14) → US2(T015-17) → US3(T018-20) → US4(T021-23)
建议顺序即编号顺序；US2/US3 可穿插并行（不同文件）
Polish(T024-27) 收尾依赖全部 US 完成
```

## Parallel Execution Examples

- Phase 2 内：T003+T005 同时写测试 → T004+T006 同时实现（纯逻辑零交集）
- US 线间：T016（layers.py）与 T018（test_query.py）无文件交集，可并行
- 同线内严格顺序：T012 依赖 T011 红、T013 依赖 T012 绿

## Implementation Strategy

- **MVP = Phase 1–3（US1 完）**：即可向 agent 说"画个矩形"看到落图
- 每条 US 完成即独立可演示增量；T009 与 T025 是两道硬闸门

## Phase 8 — v2 扩展（创始人指令：功能多样性对齐并超越竞品；契约 v2.0）

- [x] T028 [P] 先写 `tests/test_generators.py`（红）：gen_gear 齿数/点半径范围、gen_flange 孔数量与分布圆、gen_bolt 关键尺寸映射
- [x] T029 实现 `src/cad_mcp/generators.py`（绿）：bolt/flange/gear_spur 纯函数产出 items[]，复用 create_batch 落图
- [x] T030 [P] 实现 `src/cad_mcp/dims.py`：三种真尺寸标注 + hatch + mtext（COM 任务模式）
- [x] T031 [P] 实现 `src/cad_mcp/ops.py`：send_command/get_entity/delete_entities/set_layer_props/documents/blocks/arrays
- [x] T032 实现 `src/cad_mcp/vision.py`：zoom + export_screenshot（ctypes 置前 + PIL 抓屏）
- [x] T033 server.py 注册全部 21 个新工具并自测 list_tools=34
- [x] T034 真机验证：gen_flange 一键出图对比手绘版；hatch 剖面线；截图工具回传
- [x] T035 基准复测 + README(中英) + 发布检查单

## Phase 9 — v3 流水线（specs/002-nlp-plan-pipeline；契约 v2.1，+7 工具）

- [x] T036 [P] 先写 `tests/test_parser.py`（红）：黄金语句集 10 条数值级比对 + 缺失报告
- [x] T037 实现 `src/cad_mcp/parser.py`（绿）：移植前作正则库（WxH/Φ/R/角度/单位/意图）
- [x] T038 [P] 先写 `tests/test_planner.py`（红）：五类坏计划注入全拦截 + 好计划零误报
- [x] T039 实现 `src/cad_mcp/planner.py`（绿）：Plan 构建 + 四类校验 + execute 编排
- [x] T040 [P] 先写 `tests/test_sheet.py`（红）：幂等初始化判定
- [x] T041 实现 `src/cad_mcp/sheet.py`（绿）：gb-mech 五层 + A4 图框标题栏
- [x] T042 实现 `src/cad_mcp/imagegeo.py`（cv2 懒加载）+ `dwgscan.py`（即开即关）
- [x] T043 server 注册 8 新工具（含 cad_list_rulesets）→ list_tools=42
- [x] T044 真机验证：SC-7~SC-11 全跑 + 黄金语句集归档
- [x] T045 [P] 规则包引擎：JSON 外置三包（mechanical-gb 内置实检 + 建筑/化工种子）+ cad_validate_plan(ruleset) 集成 + cad_list_rulesets
- [x] T046 [P] ROADMAP.md：AutoCAD Electrical 智能元器件支持路线（待环境实测）；README 终版

## Phase 10 — 003-production-hardening（P0 四项）
- [x] T047 先写 `tests/test_session_hardening.py`（红）：断连注入写零重放、可疑态快速拒绝、泄漏上限
- [x] T048 改造 `session.py`（绿）：_suspect/_leaked/write_safe 语义；全调用点读写分类更新
- [x] T049 实现 `smoke_suite.py` 六检查 + 退出码
- [x] T050 `.github/workflows/ci.yml` + pyproject markers
- [x] T051 本机全量验证（pytest + smoke_suite 双绿）+ PRODUCTION_READINESS 回填状态

## Phase 11 — 004-p1-observability-security-soak（P1 三项）
- [x] T052 logging_setup.py JSONL 双通道 + _guard 工具级追踪（tool/duration_ms/ok）
- [x] T053 tools_meta.py WRITE_TOOLS 清单 + --read-only 模式实测拦截 + SECURITY.md
- [x] T054 soak_test.py 框架（ctypes 内存/GDI 采样）+ 120 轮短程实测零错误
- [x] T055 COMPATIBILITY.md 矩阵文档化
- [x] T056 PRODUCTION_READINESS P1 回填（8h 全量浸泡挂机项移交用户）

## Phase 12 — 工业级压力测试（创始人验收）
- [x] T057 减速器输出轴全要素零件图：7 段阶梯+双键槽长圆+A-A/B-B 移出剖面(ANSI31 剖面线)+三层尺寸链+直径引出栈×7+剖切符号+技术要求+专用标题栏 —— 121 实体 4.2s，DWG 存档 shaft_GBT1095.dwg，图层归零修复

## Phase 13 — 工业密集版迭代（创始人验收驱动）
- [x] T058 v3 密集版：越程槽×4/基准AB/形位公差框×4(放大挪净区)/粗糙度×9/九段全链/键槽12N9+t1引出 —— 200 实体，识图初审 7/10（密度/越程槽/剖面/尺寸链全过；扣分项为公差框可见性）
- [x] T059 定向修复：框格放大移净区、基准移轴承位上方 —— 复审因视觉API账户限流待补，图纸文件 shaft_v3_final.jpg 已归档供人工终验

## Phase 14 — 真实生产图对标迭代（识图模型参与验收）
- [x] T060 下载真实课设低速轴 DWG（fairyang/Course-design-of-mechanical-design），自研 cad_scan_dwg 扫描出对象构成：306 实体/RotatedDimension20/Fcf8/Leader7/Hatch10
- [x] T061 新增真对象三件套工具（dim_rotated/tolerance_frame/leader）→ 总工具 44
- [x] T062 轴 v4 重做：真 RotatedDimension×12 + Leader×9 + Fcf 模拟框×4 + 公差带代号全标 —— 实测发现 2026 COM 已弃用 AddLeader/AddTolerance，落地图元高保真模拟版
- [x] T063 排障三连：gencache 缓存污染清除 / except as e 回归 / numpy 真值歧义 —— 全部沉淀
- [x] T064 视觉终审 9/10（上版 7 分扣分项全数确认修复；AutoCAD COM 直出 JPG 取证方案落地）

## Phase 15 — 005-assembly-drawing（终极目标）
- [x] T065 编写装配图驱动脚本（双轴系剖视+啮合+轴承简化+箱体+螺栓组）
- [x] T066 序号气球系统+明细栏 BOM+技术特性表+技术要求
- [x] T067 真机落图 ≥400 实体 + DWG/JPG 双存档
- [x] T068 ★强制视觉模型终审（指数退避重试直到成功），首次评审即 8/10 达标
