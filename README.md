# CAD Direct Control Platform

> AutoCAD 直连自动化多进程微服务平台 — 从自然语言、图片、PDF、DWG 到 AutoCAD 绘图的全链路自动化。

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 架构

```
User Request
  │
  ┌└ Gateway:8000 ── HTTP Orchestration ─────→ Artifacts:8008
  │
  ├──→ [Intake:8001]      NLP 解析（中英文）
  ├──→ [Vision:8002]      OpenCV 图像识别
  ├──→ [CADPlan:8003]    多实体组合解析
  ├──→ [Validation:8004] 4类校验
  ├──→ [CAD COM:8005]     唯一 COM 拥有者
  ├──→ [Preview:8006]     截图/PDF导出（通过 cad_com 代理）
  ├──→ [DWG Scan:8007]   DWG 扫描（通过 cad_com 代理）
  └──→ [Artifacts:8008]    SQLite 工件存储
```

## 功能特性

- **自然语言输入** — 支持中英文：\"draw a 200x100 rectangle\" / \"画一个Φ30的圆\"
- **多实体组合** — 一句话解析多个图形（矩形+圆+弧+线）
- **图片识别** — OpenCV 自动检测直线、圆、矩形
- **智能规划** — 规则驱动生成可执行图纸计划
- **自动校验** — 4类校验确保图纸可执行
- **COM 隔离** — 只有 cad_com 服务持有 AutoCAD COM 引用

## 快速开始

### 前置条件

- Python 3.11+
- AutoCAD 2026（或其他支持的 CAD：浩辰 CAD、中望 CAD）
- Windows 操作系统
- Docker Desktop（Windows Containers）- 可选

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

方式一：各服务独立启动（开发模式）

```powershell
# 先启动所有依赖服务
Start-Process python -ArgumentList "-m services.artifacts.main"
Start-Process python -ArgumentList "-m services.intake.main"
Start-Process python -ArgumentList "-m services.vision.main"
Start-Process python -ArgumentList "-m services.cadplan.main"
Start-Process python -ArgumentList "-m services.validation.main"
Start-Process python -ArgumentList "-m services.cad_com.main"
Start-Process python -ArgumentList "-m services.preview.main"
Start-Process python -ArgumentList "-m services.dwg_scan.main"

# 最后启动编排网关
python -m services.gateway.main
```

方式二：Docker Compose（Windows Containers）

```powershell
docker compose up -d --build
```

### 调用示例

```bash
# 创建绘图任务
curl -X POST http://127.0.0.1:8000/job/create   -H "Content-Type: application/json"   -d '{"user_request": "draw a 200x100 rectangle", "output_level": "professional_dwg"}'

# 多实体绘图任务
curl -X POST http://127.0.0.1:8000/job/create   -H "Content-Type: application/json"   -d '{"user_request": "draw a 200x100 rectangle with a circle Phi30 inside", "output_level": "sketch"}'
```

## 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| Gateway | 8000 | HTTP 编排入口 |
| Intake | 8001 | NLP 解析引擎 |
| Vision | 8002 | OpenCV CPU 密集 |
| CADPlan | 8003 | 多实体组合解析 |
| Validation | 8004 | 4类校验 |
| CAD COM | 8005 | **唯一 COM 进程** |
| Preview | 8006 | 截图隔离（通过 COM 代理） |
| DWG Scan | 8007 | DWG 扫描（通过 COM 代理） |
| Artifacts | 8008 | 文件管理 |

## 技术栈

- **FastAPI** — 异步 Web 框架
- **httpx** — 异步 HTTP 客户端（微服务间通信）
- **OpenCV** — 计算机视觉
- **pywin32** — Windows COM 自动化
- **SQLite** — 工件存储
- **Pydantic** — 数据模型验证

## 测试

```powershell
.venv\Scripts\pytest.exe tests/ -v
# 54 passed
```

## License

MIT License. See [LICENSE](LICENSE).

## Contributing

欢迎提交 Issue 和 Pull Request。
