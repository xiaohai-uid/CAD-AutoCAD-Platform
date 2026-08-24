"""T003: result.py 统一结果与错误码（先红后绿）"""
from cad_mcp.result import (
    ok, fail, partial,
    NOT_RUNNING, NO_DOCUMENT, INVALID_PARAM, BUSY_MODAL,
    SAVE_CONFLICT, PARTIAL, COM_FAILURE,
)


def _codes():
    return {NOT_RUNNING, NO_DOCUMENT, INVALID_PARAM, BUSY_MODAL,
            SAVE_CONFLICT, PARTIAL, COM_FAILURE}


def test_ok_shape():
    r = ok("画好了", handles=["1A2"])
    assert r == {"ok": True, "message": "画好了", "handles": ["1A2"]}
    assert "error" not in r


def test_ok_with_data():
    r = ok("状态", data={"attached": True})
    assert r["data"]["attached"] is True


def test_fail_has_default_hint():
    r = fail(NOT_RUNNING, "未找到运行中的 AutoCAD")
    assert r["ok"] is False
    assert r["error"]["code"] == NOT_RUNNING
    assert r["error"]["hint"]  # 每个错误码都有人话指引


def test_all_seven_codes_have_hints():
    for c in _codes():
        assert fail(c, "x")["error"]["hint"], f"{c} 缺 hint"


def test_fail_custom_hint_overrides():
    r = fail(INVALID_PARAM, "半径非法", hint="r 必须 > 0")
    assert r["error"]["hint"] == "r 必须 > 0"


def test_partial_keeps_created_handles_and_items():
    items = [
        {"ok": True, "handle": "10"},
        {"ok": False, "error_code": INVALID_PARAM, "reason": "负半径"},
    ]
    r = partial(["10"], items, "2 个中成功 1 个")
    assert r["ok"] is False
    assert r["error"]["code"] == PARTIAL
    assert r["handles"] == ["10"]
    assert len(r["items"]) == 2
