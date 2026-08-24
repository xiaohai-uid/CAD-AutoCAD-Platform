"""真尺寸标注对象 + 填充 + 多行文本。"""
from __future__ import annotations
import math
from typing import Any

from .drawing import ParamError, _variant_pt, _get_doc
from .result import fail, ok
from .session import AutoCADSession, SessionError


def dim_aligned(session, x1, y1, x2, y2, ox, oy, text=None, layer=None) -> dict:
    if (x1, y1) == (x2, y2):
        return fail("INVALID_PARAM", "界址点重合")
    def job(app):
        doc = _get_doc(app)
        d = doc.ModelSpace.AddDimAligned(_variant_pt(x1, y1), _variant_pt(x2, y2), _variant_pt(ox, oy))
        if text:
            d.TextOverride = text
        if layer:
            d.Layer = layer
        return str(d.Handle)
    try:
        h = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    return ok("标注已创建", handles=[h])


def _circle_dim(session, mode, handle, chord_x, chord_y, leader_len, text=None, layer=None):
    def job(app):
        doc = _get_doc(app)
        ent = doc.HandleToObject(str(handle))
        fn = doc.ModelSpace.AddDimDiameter if mode == "diameter" else doc.ModelSpace.AddDimRadius
        d = fn(ent, _variant_pt(chord_x, chord_y), float(leader_len))
        if text:
            d.TextOverride = text
        if layer:
            d.Layer = layer
        return str(d.Handle)
    try:
        h = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    return ok("标注已创建", handles=[h])


def dim_diameter(session, handle, chord_x, chord_y, leader_len=5, text=None, layer=None):
    return _circle_dim(session, "diameter", handle, chord_x, chord_y, leader_len, text, layer)


def dim_radius(session, handle, chord_x, chord_y, leader_len=5, text=None, layer=None):
    return _circle_dim(session, "radius", handle, chord_x, chord_y, leader_len, text, layer)


def hatch(session, handles, pattern="ANSI31", scale=1.0, angle_deg=0.0, layer=None) -> dict:
    if not handles:
        return fail("INVALID_PARAM", "handles 不能为空")
    def job(app):
        doc = _get_doc(app)
        from win32com.client import VARIANT
        import pythoncom
        made = []
        for h in handles:                     # 每个闭合环独立一次 AppendOuterLoop
            ent = doc.HandleToObject(str(h))
            hs = doc.ModelSpace.AddHatch(0, str(pattern), True)
            hs.AppendOuterLoop(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, [ent]))
            for attr, val in (("ScaleFactor", float(scale)),
                              ("PatternScale", float(scale))):
                try:
                    setattr(hs, attr, val); break
                except Exception:
                    continue
            for attr, val in (("PatternAngle", math.radians(float(angle_deg))),):
                try:
                    setattr(hs, attr, val)
                except Exception:
                    pass
            if layer:
                hs.Layer = layer
            hs.Evaluate()
            made.append(str(hs.Handle))
        return made
    try:
        made = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    except Exception as e:
        return fail("COM_FAILURE", f"填充失败（每个句柄须为单个闭合边界）：{e}")
    return ok(f"已创建 {len(made)} 个填充", handles=made)


def draw_mtext(session, text, x, y, width, height=3.5, layer=None) -> dict:
    if not isinstance(text, str) or not text.strip():
        return fail("INVALID_PARAM", "text 不能为空")
    if width <= 0 or height <= 0:
        return fail("INVALID_PARAM", "width/height 必须 > 0")
    def job(app):
        doc = _get_doc(app)
        mt = doc.ModelSpace.AddMText(_variant_pt(x, y), float(width), str(text))
        mt.Height = float(height)
        if layer:
            mt.Layer = layer
        return str(mt.Handle)
    try:
        h = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    return ok("多行文字已创建", handles=[h])


def dim_rotated(session, x1, y1, x2, y2, dimline_x, dimline_y,
                rot_deg=0.0, text=None, layer=None) -> dict:
    """真 RotatedDimension：水平(0°)/垂直(90°)/任意角线性标注。"""
    def job(app):
        doc = _get_doc(app)
        d = doc.ModelSpace.AddDimRotated(
            _variant_pt(x1, y1), _variant_pt(x2, y2),
            _variant_pt(dimline_x, dimline_y), math.radians(float(rot_deg)))
        if text:
            d.TextOverride = text
        if layer:
            d.Layer = layer
        return str(d.Handle)
    try:
        h = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    return ok("旋转标注已创建", handles=[h])


def tolerance_frame(session, location_x, location_y, text,
                    height=None, layer=None) -> dict:
    """形位公差框格（图元高保真模拟）。

    ⚠️ 实测 AutoCAD 2026 COM 的 AddTolerance 不可用（参数无效），故以
    分隔矩形+双格文字模拟，视觉等效；真关联 Fcf 对象列入 ROADMAP。
    text 支持 "|" 或空格分隔两格。
    """
    parts = str(text).replace("|", " ").split(None, 1)
    left = parts[0] if parts else ""
    right = parts[1] if len(parts) > 1 else ""
    w1 = max(len(left), 2) * 2.0 + 3
    w2 = max(len(right), 2) * 1.8 + 4
    h = float(height or 6.0)
    x, y = float(location_x), float(location_y)

    def job(app):
        doc = _get_doc(app)
        from win32com.client import VARIANT
        import pythoncom
        pts = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                      [x, y, 0, x + w1 + w2, y, 0,
                       x + w1 + w2, y + h, 0, x, y + h, 0])
        fr = doc.ModelSpace.AddPolyline(pts)
        fr.Closed = True
        ln = doc.ModelSpace.AddLine(_variant_pt(x + w1, y),
                                    _variant_pt(x + w1, y + h))
        t1e = doc.ModelSpace.AddText(left, _variant_pt(x + 2, y + h/2 - 1.2), 2.8)
        t2e = doc.ModelSpace.AddText(right, _variant_pt(x + w1 + 2, y + h/2 - 1.2), 2.8)
        hs = [str(fr.Handle), str(ln.Handle),
              str(t1e.Handle), str(t2e.Handle)]
        if layer:
            for e in (fr, ln, t1e, t2e):
                e.Layer = layer
        return hs
    try:
        hs = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    return ok("形位公差框已创建（图元模拟）", handles=hs)


def leader_obj(session, points, annotation_text=None, layer=None,
               annotation_x=None, annotation_y=None, ann_height=3.5) -> dict:
    """引线（图元模拟）：折线箭杆 + 可选端部附注文字。

    ⚠️ 2026 COM 弃用 AcDbLeader；本实现视觉等效且稳定。"""
    if len(points) < 2:
        return fail("INVALID_PARAM", "引线至少两个点")
    def job(app):
        doc = _get_doc(app)
        from win32com.client import VARIANT
        import pythoncom
        flat = []
        for px, py in points:
            flat += [float(px), float(py), 0.0]
        pl = doc.ModelSpace.AddPolyline(
            VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat))
        hs = [str(pl.Handle)]
        if layer:
            pl.Layer = layer
        if annotation_text:
            ax = float(annotation_x if annotation_x is not None else points[-1][0] + 2)
            ay = float(annotation_y if annotation_y is not None else points[-1][1])
            te = doc.ModelSpace.AddText(str(annotation_text),
                                        _variant_pt(ax, ay), float(ann_height))
            if layer:
                te.Layer = layer
            hs.append(str(te.Handle))
        return hs
    try:
        hs = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    return ok("引线已创建", handles=hs)
