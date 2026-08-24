# Security Policy / 安全边界声明

## 威胁模型假设
**单用户、本机、可信 agent**。MCP stdio 无鉴权——任何能连上此 stdio 的进程都拥有等价于本人的 AutoCAD 操作权。

## 明示风险
| 能力 | 风险 | 缓解 |
|------|------|------|
| `cad_send_command` | 等同任意 AutoCAD 命令/LISP 执行（可间接文件操作） | 仅在可信 agent 会话使用；`--read-only` 模式下禁用 |
| `cad_save_dwg` | 可写盘任意路径（无白名单） | 路径由调用方控制；覆盖需显式 overwrite=true |
| `cad_delete_entities` / `cad_undo` | 直接删改图纸 | 单步撤销+操作日志；删除结果逐项报告 |
| 启动参数 | `--read-only` 关闭全部变更类工具 | 见 README |

## 不提供
多用户隔离 · 网络鉴权 · 审计签字级日志 · 恶意输入防御（信任 LLM 调用链）
