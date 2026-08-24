"""参数化生成器：齿轮渐开线 / 法兰 / 螺栓（纯函数产出 items，经 create_batch 落图）。"""
from __future__ import annotations
import math
from typing import Any

PTS_PER_TOOTH = 14


class ParamError(Exception):
    pass


# ============================================================ 渐开线齿轮
def _inv(a: float) -> float:
    return math.tan(a) - a


def gear_profile(z: int, module: float, bore_r: float | None = None,
                 pressure_angle: float = 20.0) -> dict[str, Any]:
    """标准渐开线直齿外齿轮近似轮廓（每齿 2*S+2 点）。"""
    z = int(z)
    if z < 6 or z > 300:
        raise ParamError("齿数 z 必须在 6..300")
    if module <= 0:
        raise ParamError("模数必须 > 0")
    pa = math.radians(pressure_angle)
    rp = module * z / 2.0
    rb = rp * math.cos(pa)
    ra = rp + module
    rf = rp - 1.25 * module
    s_half = (math.pi * module / 4.0) / rp
    inv_pa = _inv(pa)
    S = 4
    per_tooth = 2 * S + 2

    def alpha_at(r):
        return math.acos(min(1.0, rb / r))

    pts = []
    for k in range(z):
        th0 = 2.0 * math.pi * k / z
        for side in (1, -1):
            for i in range(S):
                r_i = max(rb, rf) + (ra - max(rb, rf)) * i / (S - 1)
                a_i = alpha_at(r_i)
                th = th0 + side * (s_half + inv_pa - _inv(a_i))
                rr = max(r_i, rf)
                pts.append([rr * math.cos(th), rr * math.sin(th)])
        pts.append([ra * math.cos(th0), ra * math.sin(th0)])
        th_root = th0 - math.pi / z
        pts.append([rf * math.cos(th_root), rf * math.sin(th_root)])

    return {"cx": 0.0, "cy": 0.0, "points": pts,
            "meta": {"rp": rp, "rb": rb, "ra": ra, "rf": rf, "z": z,
                     "module": module, "pressure_angle": pressure_angle,
                     "pts_per_tooth": per_tooth}}


# ============================================================ 法兰
def flange_items(D: float, K: float, n: int, L: float, b: float,
                 d1: float, A: float, f: float = 2.0,
                 scale: float = 0.5, origin: list[float] | None = None) -> list[dict]:
    """板式平焊法兰双视图（几何 items；标注留给 agent）。"""
    ox, oy = (origin or [0, 0])
    R_D, R_K, R_d1, R_A = D / 2 * scale, K / 2 * scale, d1 / 2 * scale, A / 2 * scale
    r_L = L / 2 * scale
    its: list[dict] = []

    # 端面图 @ origin
    its += [
        {"kind": "circle", "cx": ox, "cy": oy, "r": R_D, "layer": "OUTLINE"},
        {"kind": "circle", "cx": ox, "cy": oy, "r": R_K, "layer": "CENTER"},
        {"kind": "circle", "cx": ox, "cy": oy, "r": R_d1, "layer": "OUTLINE"},
        {"kind": "circle", "cx": ox, "cy": oy, "r": R_A, "layer": "OUTLINE"},
    ]
    for k in range(int(n)):
        a = math.radians(22.5 + 45 * k)
        its.append({"kind": "circle", "cx": ox + R_K * math.cos(a),
                    "cy": oy + R_K * math.sin(a), "r": r_L, "layer": "OUTLINE"})
    ext = R_D * 1.12
    its += [
        {"kind": "line", "x1": ox - ext, "y1": oy, "x2": ox + ext, "y2": oy, "layer": "CENTER"},
        {"kind": "line", "x1": ox, "y1": oy - ext, "x2": ox, "y2": oy + ext, "layer": "CENTER"},
    ]

    # 剖视 @ 右侧：轴线同高；板厚 b*scale；突面 f*scale
    sx = ox + R_D + 20          # 左端面 x
    t = b * scale
    tf = max(f * scale, 0.8)
    yT1, yB1 = oy + R_d1, oy - R_d1       # 内孔上下
    yT2, yB2 = oy + R_D, oy - R_D         # 外径上下
    yF1, yF2 = oy + R_d1 + tf, oy - R_d1 - tf   # 突面台阶段
    its += [
        {"kind": "polyline", "closed": True, "layer": "OUTLINE",
         "points": [[sx - tf, yT1], [sx - tf, yF1], [sx, yF1], [sx, yT2], [sx + t, yT2], [sx + t, yT1]]},
        {"kind": "polyline", "closed": True, "layer": "OUTLINE",
         "points": [[sx - tf, yB1], [sx - tf, yF2], [sx, yF2], [sx, yB2], [sx + t, yB2], [sx + t, yB1]]},
        {"kind": "line", "x1": sx - t, "y1": oy, "x2": sx + t + 15, "y2": oy, "layer": "CENTER"},
    ]
    return its


# ============================================================ 螺栓 GB/T 5782
GBT5782_TABLE = {8: (13, 5.3), 10: (16, 6.4), 12: (18, 7.5),
                 16: (24, 10.0), 20: (30, 12.5)}


def bolt_items(d: float, L: float) -> dict[str, Any]:
    d = float(d); L = float(L)
    if d not in GBT5782_TABLE:
        raise ParamError(f"暂支持规格 {sorted(GBT5782_TABLE)}，M{g} 未收录".replace('g', str(d)))
    s, k = GBT5782_TABLE[d]
    e = s / math.cos(math.radians(30))
    b = min(L, 2 * d + 6)

    its: list[dict] = []
    # 端面图（六边形对边距 s 竖直）@ 原点
    Rc = s / math.sqrt(3)
    hexpts = [[Rc * math.cos(math.radians(a)), Rc * math.sin(math.radians(a))]
              for a in range(0, 360, 60)]
    its += [
        {"kind": "polyline", "points": hexpts, "closed": True, "layer": "OUTLINE"},
        {"kind": "circle", "cx": 0, "cy": 0, "r": d / 2, "layer": "OUTLINE"},
        {"kind": "line", "x1": -Rc - 4, "y1": 0, "x2": Rc + 4, "y2": 0, "layer": "CENTER"},
        {"kind": "line", "x1": 0, "y1": -Rc - 4, "x2": 0, "y2": Rc + 4, "layer": "CENTER"},
    ]
    # 主视图 @ x 从 2*Rc+25 起，轴线 y=0
    x0 = 2 * Rc + 25           # 头背
    xs = x0 + k                # 支承面
    xe = xs + L                # 杆端
    xb = xe - b                # 螺纹起始
    hd, hdd = d / 2, d / 2 - 0.95   # 牙底
    its += [
        {"kind": "polyline", "closed": True, "layer": "OUTLINE",
         "points": [[xs, -hd], [x0, -hd], [x0 + 1.5, -hd - k + 2.2],
                    [x0 + k - 1.5, -hd - k], [xs - 1.5, -hd - k],
                    [xs, -hd - k + 2.2]]},
        {"kind": "line", "x1": xs, "y1": -hd, "x2": xe, "y2": -hd, "layer": "OUTLINE"},
        {"kind": "line", "x1": xs, "y1": hd, "x2": xe, "y2": hd, "layer": "OUTLINE"},
        {"kind": "line", "x1": xe, "y1": -hd, "x2": xe, "y2": hd, "layer": "OUTLINE"},
        {"kind": "line", "x1": xb, "y1": -hd, "x2": xb, "y2": hd, "layer": "OUTLINE"},
        {"kind": "line", "x1": xb + 1, "y1": -hdd, "x2": xe - 1.5, "y2": -hdd, "layer": "THIN"},
        {"kind": "line", "x1": xb + 1, "y1": hdd, "x2": xe - 1.5, "y2": hdd, "layer": "THIN"},
        {"kind": "line", "x1": x0 - 6, "y1": 0, "x2": xe + 7, "y2": 0, "layer": "CENTER"},
        {"kind": "text", "text": f"M{int(d)}-6g x {int(L)}", "x": xs + L * .25,
         "y": hd + 4, "height": 3.5, "layer": "DIM"},
    ]
    return {"items": its, "meta": {"d": d, "L": L, "b": b, "s": s, "k": k, "e": round(e, 2)}}
