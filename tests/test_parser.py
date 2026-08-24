"""T036: 黄金语句集——确定性解析，数值级比对（SC-7）"""
from cad_mcp.parser import parse_text

GOLDEN = [
    # (text, expect_fields)
    ("画一个Φ30的圆", {"circle_d": 30}),
    ("draw a circle with radius 15", {"circle_r": 15}),
    ("200x100 矩形", {"rect": (200, 100)}),
    ("draw a 100x50 rectangle", {"rect": (100, 50)}),
    ("半径R10的圆", {"circle_r": 10}),
    ("直径为50的孔", {"circle_d": 50}),
    ("45°斜线", {"angle": 45}),
    ("draw a line from (10,20) to (30,40)", {"line_pts": ((10, 20), (30, 40))}),
    ("开槽尺寸 30x20 和 Φ12", {"rect": (30, 20), "circle_d": 12}),
    ("M12 bolt on 5mm plate", {"unit": "mm"}),
]


def _find(entities, kind):
    return [e for e in entities if e["kind"] == kind]


def test_golden_set_full_coverage():
    for text, exp in GOLDEN:
        r = parse_text(text)
        assert not r["missing"] or exp.get("unit"), f"{text!r} 意外缺失: {r['missing']}"
        if "circle_d" in exp:
            hits = [e for e in _find(r["entities"], "circle") if abs(e["params"]["diameter"] - exp["circle_d"]) < 1e-9]
            assert hits, f"{text!r} 未解析出 Φ{exp['circle_d']}"
        if "circle_r" in exp:
            hits = [e for e in _find(r["entities"], "circle") if abs(e["params"]["radius"] - exp["circle_r"]) < 1e-9]
            assert hits, f"{text!r} 未解析出 R{exp['circle_r']}"
        if "rect" in exp:
            w, h = exp["rect"]
            hits = [e for e in _find(r["entities"], "rectangle")
                    if abs(e["params"]["width"] - w) < 1e-9 and abs(e["params"]["height"] - h) < 1e-9]
            assert hits, f"{text!r} 未解析出 {w}x{h}"


def test_angle_extracted():
    r = parse_text("45°斜线")
    lines = _find(r["entities"], "line")
    assert any(abs(l["params"].get("angle", 0) - 45) < 1e-9 for l in lines)


def test_line_endpoints():
    r = parse_text("draw a line from (10,20) to (30,40)")
    lines = _find(r["entities"], "line")
    hit = [l for l in lines if l["params"].get("x1") == 10 and l["params"].get("y2") == 40]
    assert hit


def test_unit_detection():
    assert parse_text("5mm plate")["unit"] == "mm"
    assert parse_text("长度 25 inch")["unit"] == "inch"
    assert parse_text("随便说说")["unit"] == "mm"  # 默认


def test_intent_classification():
    assert parse_text("画一个圆")["intent"] == "create"
    assert parse_text("edit the shape")["intent"] == "edit"


def test_missing_reported_not_fabricated():
    r = parse_text("帮我画个东西")
    assert r["intent"] == "create"
    assert r["entities"] == []
    assert "dimensions" in r["missing"]


def test_mixed_cn_en_sentence():
    r = parse_text("draw a Φ30 圆 and 100x50 rect")
    assert len(_find(r["entities"], "circle")) >= 1
    assert any(abs(e["params"]["width"] - 100) < 1e-9 for e in _find(r["entities"], "rectangle"))
