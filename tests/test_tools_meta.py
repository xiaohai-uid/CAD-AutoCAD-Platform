"""tools_meta 只读清单判定"""
from cad_mcp.tools_meta import is_write_tool


def test_query_tools_are_read_only():
    for n in ["cad_status", "cad_query_entities", "cad_parse_text",
              "cad_validate_plan", "cad_list_layers"]:
        assert not is_write_tool(n), f"{n} 应属只读"


def test_mutating_tools_flagged():
    for n in ["cad_draw_line", "cad_create_batch", "cad_undo",
              "cad_delete_entities", "gen_flange", "cad_send_command",
              "cad_save_dwg", "cad_execute_plan"]:
        assert is_write_tool(n), f"{n} 应属变更类"


def test_unknown_defaults_to_write():
    assert is_write_tool("some_future_tool")
