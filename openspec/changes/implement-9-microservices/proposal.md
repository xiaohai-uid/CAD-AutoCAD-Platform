## Why

cad-direct-control-platform 的 9 个微服务骨架已搭建（FastAPI + 路由 + Pydantic 模型），但全部为桩代码，无法完成实际的 CAD 自动化流程。需要给每个服务注入真实业务逻辑，使完整的 11 步工作流（Intake → Vision → CADPlan → Validation → Execute → Save → Preview → Artifacts）端到端可运行，让 AutoCAD 2026 通过 COM 接口接收自然语言指令并产出 DWG + 预览 + 日志。

## What Changes

- **Gateway (8000)**: 同步编排引擎，实现 Job CRUD + 工作流状态机 + 逐级调用下游服务
- **Intake (8001)**: 输入解析引擎，检测语言意图、文件类型、提取尺寸/几何关键词
- **Vision (8002)**: 图像几何要素检测引擎（OpenCV），识别直线/圆/矩形/弧并估算尺寸
- **CADPlan (8003)**: CAD 计划生成引擎，输入自然语言 + Vision 分析 → 结构化 Plan JSON
- **Validation (8004)**: 计划校验引擎，检查完整性/一致性/可执行性，生成假设清单
- **CAD COM (8005)**: AutoCAD COM 执行引擎，连接 `cad_controller.py` 实现绘图/保存/图层管理
- **Preview (8006)**: 预览截图引擎，通过 COM+OS 工具捕获 AutoCAD 视口截图
- **DWG Scan (8007)**: DWG 解析引擎，读取现有图纸的图层/实体/尺寸信息
- **Artifacts (8008)**: 产物归档引擎，管理 DWG/预览/日志/假设清单的文件存取与元数据

## Capabilities

### New Capabilities

- `gateway-orchestrator`: Job CRUD + 11 步工作流同步编排 + 下游服务级联调用 + 假设管理
- `intake-parser`: 用户输入解析（意图检测、输入类型分类、尺寸/几何关键词提取）
- `vision-geometry`: 图像几何检测（OpenCV 直线/圆/矩形检测、尺寸估算、置信度输出）
- `cadplan-generator`: CAD 计划生成（rule-based 实体布局 + 尺寸计算 + 图层分配 + 假设标记）
- `validation-engine`: 计划校验（完整性检查、尺寸一致性、单位验证、blocking/non-blocking 分类）
- `cad-com-executor`: AutoCAD COM 执行（连接、新建/打开图纸、逐命令绘图、保存、图层管理）
- `preview-capture`: 视口截图与 PDF 导出（COM Export + win32 截图兜底）
- `dwg-scanner`: DWG 文件信息提取（COM 遍历实体、图层列表、尺寸提取）
- `artifact-manager`: 产物文件管理（目录结构、元数据 SQLite、四件套查询 API）

### Modified Capabilities

无（首次实现，尚无已发布的 spec）

## Impact

- **代码**: 修改 9 个 `services/*/main.py`，新增 `services/*/engine.py` 实现各服务核心逻辑
- **依赖新增**: 仅 Vision service 新增 `opencv-python-headless`；其余依赖均已存在
- **API 路径**: 各服务 API 路径按 SKILL.md 规范对齐
- **AutoCAD**: 需在运行时保持 AutoCAD 2026 打开

## 架构概览

```
User/Skill Subagent
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Gateway (8000) — 同步编排引擎                    │
│  POST /job/create → orchestrator workflow        │
└──┬──┬──┬──┬──┬──┬──┬──┬──┬──────────────────────┘
   │  │  │  │  │  │  │  │  │
   ▼  ▼  ▼  ▼  ▼  ▼  ▼  ▼  ▼
 Intake  Vision  CADPlan  Validation  CAD COM  Preview  DWG Scan  Artifacts
 (8001)  (8002)  (8003)   (8004)      (8005)   (8006)   (8007)    (8008)
```

### 工作流

```
create_job → intake → [if files] vision → cadplan → validation
→ [if questions] wait_confirm → cad_com.execute → cad_com.save
→ preview.capture → artifacts.store → return 四件套
```
