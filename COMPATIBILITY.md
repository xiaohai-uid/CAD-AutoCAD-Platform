# Compatibility Matrix 兼容性矩阵

| 环境 | 状态 |
|------|------|
| Windows 11 + AutoCAD 2026 简体中文完整版 + Python 3.12 | ✅ 全量实测（本机） |
| AutoCAD 2022–2025（COM 接口向后兼容预期） | ⬜ 未测，理论可用 |
| AutoCAD LT（无 COM） | ❌ 设计上不支持 |
| 浩辰/GstarCAD/ZWCAD（兼容 COM ProgID 路线） | ⬜ 未测 |
| AutoCAD Electrical | 🧭 ROADMAP 待环境实测 |
| 非 Windows | ❌（live 模式）；ezdxf headless 为未来路线 |

> 声明：未列入 ✅ 的组合不构成承诺。欢迎 PR 回报实测结果补充本表。
