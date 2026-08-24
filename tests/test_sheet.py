"""T040: gb-mech 模板幂等判定（纯函数）"""
from cad_mcp.sheet import GB_MECH_LAYERS, layers_to_create


def test_template_has_five_layers():
    assert len(GB_MECH_LAYERS) == 5
    names = [n for n, _, _ in GB_MECH_LAYERS]
    assert set(names) == {"轮廓线", "中心线", "标注", "填充", "文字"}
    center = [l for n, c, l in GB_MECH_LAYERS if n == "中心线"][0]
    assert center == "CENTER"


def test_all_missing_creates_all():
    plan = layers_to_create(existing=set())
    assert {n for n, _, _ in plan} == {"轮廓线", "中心线", "标注", "填充", "文字"}


def test_idempotent_partial():
    plan = layers_to_create(existing={"轮廓线", "标注"})
    assert {n for n, _, _ in plan} == {"中心线", "填充", "文字"}


def test_idempotent_full_noop():
    existing = {n for n, _, _ in GB_MECH_LAYERS}
    assert layers_to_create(existing=existing) == []
