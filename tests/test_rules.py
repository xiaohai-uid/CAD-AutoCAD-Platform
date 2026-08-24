"""T045: 行业规则包引擎"""
from cad_mcp.rules_engine import list_rulesets, load_ruleset, apply_ruleset


def test_three_packs_shipped():
    ids = {r["id"] for r in list_rulesets()}
    assert {"mechanical-gb", "architectural-gb-seed", "chemical-pid-seed"} <= ids


def test_load_unknown_none():
    assert load_ruleset("no-such") is None


def test_apply_unknown_returns_error_issue():
    iss = apply_ruleset({"entities": []}, "no-such")
    assert iss[0]["code"] == "RULESET_NOT_FOUND"


def test_mechanical_missing_center_layer_fires():
    plan = {"layers": [{"name": "OUTLINE"}],
            "entities": [{"kind": "circle", "params": {"radius": 10}}]}
    issues = apply_ruleset(plan, "mechanical-gb")
    codes = [i["code"] for i in issues]
    assert any(c.startswith("M-001") for c in codes)
    assert any(c.startswith("M-004") for c in codes)


def test_positive_params_catches_negative():
    plan = {"entities": [{"kind": "rectangle",
                          "params": {"width": -20, "height": 10}}]}
    issues = apply_ruleset(plan, "mechanical-gb")
    assert any(i["code"].endswith("nonpositive") and i["severity"] == "error"
               for i in issues)


def test_clean_plan_zero_issues():
    plan = {"layers": [{"name": "轮廓线"}, {"name": "中心线"}, {"name": "文字"}],
            "entities": [{"kind": "circle", "params": {"radius": 15}}],
            "texts": [{"text": "法兰盘", "x": 0, "y": 40, "height": 5},
                      {"text": "图号 CAD-MCP-E2E", "x": 200, "y": 12, "height": 3.2}]}
    assert apply_ruleset(plan, "mechanical-gb") == []
