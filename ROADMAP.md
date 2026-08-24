# Roadmap

## v2.x 已交付
34→41 工具 · Plan-Validate-Execute · 行业规则包引擎（3 包）· 图片转几何 · DWG 扫描 · 视觉闭环 · 公开延迟基准

## 待验证 / 规划中
- **AutoCAD Electrical 智能元器件支持**：需 Electrical 环境实测其 COM 暴露面（目录号/线号/端子排）。
  当前 `insert_block` 可放置符号库哑块；智能元数据层待验证。**状态：等环境**
- ezdxf 无头后端（无 AutoCAD 环境用户）
- 行业规则包扩充：建筑 GB/T 50001 全量、化工 HG/T PID 符号库（现仅种子包，需专业校准）
- CI（GitHub Actions）+ PyPI 发包 + 演示 GIF
- 长期：基于视觉模型的设计合理性推理（结构/工艺可行性），即"AI 测评平台"
