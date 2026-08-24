"""T038: Plan 模型 + 四类校验 + 解析衔接"""
import pytest
from cad_mcp.parser import parse_text
from cad_mcp.planner import plan_from_parse, validate_plan


def _errors(issues): return [i for i in issues if i["severity"] == "error"]


def test_good_plan_passes_no_errors():
    plan = {
        "layers": [{"name": "OUTLINE"}],
        "entities": [
            {"id": "c1", "kind": "circle", "params": {"radius": 15}, "layer": "OUTLINE"},
            {"id": "r1", "kind": "rectangle", "params": {"width": 100, "height": 50}},
        ],
        "dimensions": [], "texts": [],
        "assumptions": [], "warnings": [], "unit": "mm",
    }
    issues = validate_plan(plan)
    assert _errors(issues) == []
    # 圆存在但未定义中心线层 → professional warning 而非 error
    assert any(i["category"] == "professional" for i in issues)


def test_empty_entities_is_completeness_error():
    issues = validate_plan({"entities": [], "unit": "mm"})
    assert any(i["code"] == "COMPLETE_EMPTY" for i in _errors(issues))


def test_negative_radius_executability_error():
    plan = {"entities": [{"kind": "circle", "params": {"radius": -5}}], "unit": "mm"}
    errs = _errors(validate_plan(plan))
    assert any(i["category"] == "executability" for i in errs)


def test_unknown_layer_reference_consistency_error():
    plan = {"layers": [{"name": "A"}],
            "entities": [{"kind": "line", "params": {"x1": 0, "y1": 0, "x2": 1, "y2": 1},
                          "layer": "不存在层"}],
            "unit": "mm"}
    errs = _errors(validate_plan(plan))
    assert any(i["category"] == "consistency" for i in errs)


def test_duplicate_ids_consistency_error():
    plan = {"entities": [
        {"id": "x", "kind": "circle", "params": {"radius": 5}},
        {"id": "x", "kind": "circle", "params": {"radius": 6}}], "unit": "mm"}
    assert any(i["code"] == "DUP_ID" for i in _errors(validate_plan(plan)))


def test_out_of_bounds_executability_error():
    plan = {"entities": [{"kind": "circle",
                          "params": {"radius": 5, "cx": 10 ** 7, "cy": 0}}], "unit": "mm"}
    assert any(i["category"] == "executability" for i in _errors(validate_plan(plan)))


# ---------- parse → plan 衔接 ----------
def test_plan_from_parse_normalizes_circle_and_records_assumptions():
    pr = parse_text("画一个Φ30的圆")
    plan = plan_from_parse(pr)
    ent = plan["entities"][0]
    assert ent["kind"] == "circle" and abs(ent["params"]["radius"] - 15) < 1e-9
    assert isinstance(plan["assumptions"], list) and plan["assumptions"]  # 默认原点假设已记录


def test_plan_from_parse_angle_line_gets_warning_and_default_len():
    plan = plan_from_parse(parse_text("45°斜线"))
    line = [e for e in plan["entities"] if e["kind"] == "line"][0]
    assert abs(line["params"]["x2"] - line["params"]["x1"]) > 0   # 已按默认长度展开端点
    assert any("长度" in w or "length" in w.lower() for w in plan["warnings"])


def test_non_mm_unit_recorded_as_assumption():
    plan = plan_from_parse(parse_text("draw a 2x1 rectangle, unit inch"))
    assert plan["unit"] == "inch"
    assert any(a["field"] == "unit" for a in plan["assumptions"])
