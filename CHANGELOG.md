# Changelog

## v2.0.0 (2026-08-24)

**完全重构**：从九引擎微服务平台重构为单进程 MCP 服务。

### 新增
- 44 个 MCP 工具（绘图/标注/填充/参数化生成器/视觉闭环/理解规划流水线）
- Plan-Validate-Execute 三段式（Plan 含 assumptions/warnings 透传）
- 行业规则包引擎（mechanical-gb 内置 + JSON 外置扩展）
- 写防重放语义（write_safe）
- 可疑态熔断 + 泄漏上限
- 结构化 JSONL 日志双通道
- --read-only 模式
- 浸泡测试框架（ctypes 内存/GDI 采样）
- 冒烟套件（六检查，exit 码化）

### 移除
- 九微服务架构（Gateway/Intake/Vision/CADPlan/Validation/CAD-COM/Preview/DWG-Scan/Artifacts）
- Docker/docker-compose 部署（MCP stdio 不需要容器化）
- HTTP REST 端点

### 设计决策
- 微服务 → 单进程：COM 唯一拥有者原则在进程内以 ComExecutor 单线程实现，
  消除跨进程 COM 序列化的全部复杂度
- 正则解析器从 Intake 引擎移植，Plan 模型从 CADPlanEngine 继承——
  九引擎的思想精华保留，架构按 MCP 语境重构

## v1.0.0 (2026-07)
前作九引擎微服务平台原型。
