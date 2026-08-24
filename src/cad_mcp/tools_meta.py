"""工具元数据：只读模式判定（FR-18，纯函数可测）。"""
from __future__ import annotations

READ_ONLY_TOOLS = frozenset({
    # 查询/状态类
    "cad_status", "cad_query_entities", "cad_get_entity",
    "cad_list_layers", "cad_list_documents", "cad_list_blocks",
    "cad_list_rulesets",
    # 计划前段（纯数据不落图）
    "cad_parse_text", "cad_plan", "cad_validate_plan",
})


def is_write_tool(name: str) -> bool:
    """不在 READ_ONLY 清单即视为变更类（保守默认）。"""
    return name not in READ_ONLY_TOOLS
