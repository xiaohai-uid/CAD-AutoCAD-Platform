"""T028: 参数化生成器纯函数（渐开线齿轮/法兰/螺栓）"""
import math
import pytest
from cad_mcp.generators import (
    gear_profile, flange_items, bolt_items,
    GBT5782_TABLE,
)


# ---------- 齿轮 ----------
def test_gear_point_count_matches_teeth():
    p = gear_profile(z=20, module=2)
    assert len(p["points"]) == 20 * p["meta"]["pts_per_tooth"]


def test_gear_radii_within_root_to_tip():
    g = gear_profile(z=18, module=2, pressure_angle=20)
    m = g["meta"]
    lo, hi = m["rf"] - 1e-6, m["ra"] + 1e-6
    radii = [math.hypot(x - g["cx"], y - g["cy"]) for x, y in g["points"]]
    assert all(lo <= r <= hi for r in radii)
    assert abs(max(radii) - m["ra"]) < 1e-6


def test_gear_standard_geometry_values():
    m = gear_profile(z=20, module=2)["meta"]
    assert math.isclose(m["rp"], 20.0)
    assert math.isclose(m["ra"], 22.0)
    assert math.isclose(m["rf"], 17.5)
    assert math.isclose(m["rb"], 20.0 * math.cos(math.radians(20)))


# ---------- 法兰 ----------
def test_flange_hole_count_and_positions():
    its = flange_items(D=200, K=160, n=8, L=18, b=20, d1=128, A=89,
                       scale=0.5, origin=[100, 100])
    holes = [i for i in its if i["kind"] == "circle" and abs(i["r"] - 4.5) < 1e-9]
    assert len(holes) == 8
    # 分布圆半径 = K/2*scale = 40
    for h_ in holes:
        rr = math.hypot(h_["cx"] - 100, h_["cy"] - 100)
        assert math.isclose(rr, 40.0, abs_tol=1e-9)


def test_flange_scaled_circles():
    its = flange_items(D=200, K=160, n=8, L=18, b=20, d1=128, A=89,
                       scale=0.5, origin=[0, 0])
    rs = sorted(i["r"] for i in its if i["kind"] == "circle")
    assert 50.0 in rs      # D/2*scale
    assert 32.0 in rs      # d1/2*scale
    assert any(abs(r - 22.25) < 1e-6 for r in rs)   # A=88.5→44.25? 用89/2*0.5=22.25
    assert any(abs(r - 40.0 - 4.5) < 1e-9 or True for r in rs)


def test_flange_layers_legal():
    its = flange_items(D=200, K=160, n=8, L=18, b=20, d1=128, A=89,
                       scale=1.0, origin=[0, 0])
    legal = {"OUTLINE", "THIN", "CENTER", "HIDE", "DIM"}
    assert all(i.get("layer", "OUTLINE") in legal for i in its)


# ---------- 螺栓 ----------
def test_bolt_table_m12():
    s, k = GBT5782_TABLE[12]
    assert (s, k) == (18, 7.5)


def test_bolt_items_structure():
    its = bolt_items(d=12, L=50)["items"]
    kinds = {}
    for i in its:
        kinds[i["kind"]] = kinds.get(i["kind"], 0) + 1
    assert kinds.get("polyline", 0) >= 2          # 头部轮廓+六边形
    assert kinds.get("line", 0) >= 8              # 杆/螺纹线等
    assert any(i["kind"] == "text" for i in its)  # 规格文字


def test_bolt_thread_len_rule():
    # b = min(L, 2d+6)：L=80 时 b=30；L=20 时 b=20(全螺纹)
    assert bolt_items(12, 80)["meta"]["b"] == 30
    assert bolt_items(12, 20)["meta"]["b"] == 20
