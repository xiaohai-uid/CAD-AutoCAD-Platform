# CAD Direct Control Platform

> AutoCAD 2026 直连自动化多进程微服务平台 — 从自然语言、图片、PDF、DWG 到 AutoCAD 绘图的全链路自动化。

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 简介

CAD Direct Control Platform 是一个基于 FastAPI 的多进程微服务架构，通过 Windows COM 自动化控制 AutoCAD，实现从输入解析到图纸输出的完整工作流。支持中文/英文自然语言输入，图片/PDF 几何识别，以及智能图纸规划与校验。

## 架构

```
User Request
  │
  ▼
[Gateway:8000] ──── 11-Step Workflow ────→ [Artifacts:8008]
  │
  ├──→ [Intake:8001]      NLP 解析、正则提取尺寸/意图/单位
  ├──→ [Vision:8002]      OpenCV 管线（Canny → Hough → 轮廓检测）
  ├──→ [CADPlan:8003]     规则驱动生成 CAD 执行计划（5图层分配）
  ├──→ [Validation:8004]  4类校验（完整性/一致性/可执行性/专业度）
  ├──→ [CAD COM:8005]     COM 桥封装，逐实体执行
  ├──→ [Preview:8006]     截图导出 + PDF 打印
  ├──→ [DWG Scan:8007]    COM 遍历现有 DWG 文件
```

## 功能特性

- **自然语言输入** — `draw a 200x100 rectangle` / `画一个Φ30的圆`
- **图片识别** — OpenCV 自动检测直线、圆、矩形
- **PDF 分析** — 扫描件转图像后识别几何
- **DWG 扫描** — 读取现有图纸实体信息
- **智能规划** — 规则驱动生成可执行图纸计划
- **自动校验** — 4类校验确保图纸可执行
- **实时预览** — 截图 + PDF 导出

## 端口分配

| 服务 | 端口 | 隔离 |
|------|------|------|
| Gateway | 8000 | 编排入口 |
| Intake | 8001 | |
| Vision | 8002 | CPU 密集 |
| CADPlan | 8003 | |
| Validation | 8004 | |
| CAD COM | 8005 | **COM 进程隔离** |
| Preview | 8006 | **截图隔离** |
| DWG Scan | 8007 | |
| Artifacts | 8008 | 文件管理 |

## 快速开始

### 前置条件

- Python 3.11+
- AutoCAD 2026（或其他支持的 CAD：浩辰 CAD、中望 CAD）
- Windows 操作系统

### 安装

```powershell
# 创建虚拟环境
python -m venv .venv
.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 验证安装
pytest tests/ -v
```

### 启动服务

每个服务独立运行：

```powershell
# Gateway（编排入口）
python -m services.gateway.main

# 依次启动其他服务...
python -m services.intake.main
python -m services.vision.main
python -m services.cadplan.main
python -m services.validation.main
python -m services.cad_com.main
python -m services.preview.main
python -m services.dwg_scan.main
python -m services.artifacts.main
```

### 调用示例

```bash
# 创建绘图任务
curl -X POST http://127.0.0.1:8000/job/create \
  -H "Content-Type: application/json" \
  -d '{"user_request": "draw a 200x100 rectangle", "output_level": "professional_dwg"}'
```

## 项目结构

```
├── cad_mcp_bridge/     CAD COM 桥接层（已验证可用）
├── config/             配置文件
├── docs/               文档和规格说明
├── openspec/           OpenSpec 规格文档
├── services/           9 个微服务
│   ├── intake/         NLP 解析引擎
│   ├── vision/         OpenCV 图像识别引擎
│   ├── cadplan/        CAD 执行计划生成
│   ├── validation/     4 类图纸校验
│   ├── cad_com/        COM 执行引擎
│   ├── preview/        预览/截图引擎
│   ├── dwg_scan/       DWG 文件扫描
│   ├── artifacts/      工件持久化管理
│   └── gateway/        编排网关
├── shared/             共享模型和配置
├── tests/              38 个单元测试（全部通过）
└── skill/              Reasonix Subagent Skill
```

## 技术栈

- **FastAPI** — 异步 Web 框架
- **httpx** — 异步 HTTP 客户端
- **OpenCV** — 计算机视觉
- **pywin32** — Windows COM 自动化
- **SQLite** — 工件存储
- **Pydantic** — 数据模型验证

## 测试

```powershell
.venv\Scripts\pytest.exe tests/ -v
# 38 passed
```

## License

MIT License. See [LICENSE](LICENSE).

## Contributing

欢迎提交 Issue 和 Pull Request。请先阅读项目的 OpenSpec 规格文档。
