"""绘图领域层：纯校验器（可离线测）+ COM 创建器 + 尽力而为批量分派（Q2）。"""
from __future__ import annotations
import math
from typing import Any

from .result import ok, partial, fail, INVALID_PARAM
from .session import AutoCADSession, SessionError

MAX_BATCH = 200
CN_STYLE = "MCP_CN"  # D5：独立中文样式，不动用户 Standard


class ParamError(Exception):
    """参数非法；str(e) 即给人看的原因。"""


# ---------------------------------------------------------------- 校验器（纯）
def _f(v: Any, name: str) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        raise ParamError(f"{name} 必须是数字，得到 {v!r}")


def validate_item(it: dict[str, Any]) -> None:
    """按契约校验单个图元参数；不合法抛 ParamError，合法静默返回。"""
    kind = it.get("kind")
    layer = it.get("layer")
    if layer is not None:
        if not isinstance(layer, str) or not (1 <= len(layer) <= 255):
            raise ParamError("layer 名必须是非空且 ≤255 字符的字符串")

    if kind == "line":
        x1, y1, x2, y2 = (_f(it[k], k) for k in ("x1", "y1", "x2", "y2"))
        if (x1, y1) == (x2, y2):
            raise ParamError("直线的起点与终点不能重合")
    elif kind == "circle":
        if not _f(it.get("r"), "r") > 0:
            raise ParamError(f"半径 r 必须 > 0，得到 {it.get('r')}")
        _f(it.get("cx"), "cx"); _f(it.get("cy"), "cy")
    elif kind == "arc":
        if not _f(it.get("r"), "r") > 0:
            raise ParamError(f"半径 r 必须 > 0")
        _f(it.get("start_angle"), "start_angle"); _f(it.get("end_angle"), "end_angle")
        _f(it.get("cx"), "cx"); _f(it.get("cy"), "cy")
    elif kind == "polyline":
        pts = it.get("points")
        if not isinstance(pts, list) or len(pts) < 2:
            raise ParamError("polyline 至少需要 2 个点")
        if it.get("closed") and len(pts) < 3:
            raise ParamError("闭合 polyline 至少需要 3 个点")
        flat = []
        for p in pts:
            if not (isinstance(p, (list, tuple)) and len(p) == 2):
                raise ParamError("points 每项必须是 [x, y]")
            flat.append((_f(p[0], "x"), _f(p[1], "y")))
        for a, b in zip(flat, flat[1:]):
            if a == b:
                raise ParamError("polyline 存在连续重复点")
    elif kind == "rectangle":
        w, h = _f(it.get("w"), "w"), _f(it.get("h"), "h")
        if w <= 0 or h <= 0:
            raise ParamError(f"矩形 w/h 必须 > 0，得到 w={it.get('w')}, h={it.get('h')}")
        _f(it.get("x"), "x"); _f(it.get("y"), "y")
    elif kind == "text":
        t = it.get("text")
        if not isinstance(t, str) or not t.strip():
            raise ParamError("text 不能为空")
        h = it.get("height", 3.5)
        if not float(h) > 0:
            raise ParamError(f"字高 height 必须 > 0，得到 {h}")
        _f(it.get("x"), "x"); _f(it.get("y"), "y")
    else:
        raise ParamError(f"未知图元类型 kind={kind!r}；"
                         f"可选 line/circle/arc/polyline/rectangle/text")


# ------------------------------------------------- COM 核心（全部在单个任务内执行）
def _variant_pt(x: float, y: float):
    import pythoncom
    from win32com.client import VARIANT
    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, 0.0])


def _variant_flat(points):
    import pythoncom
    from win32com.client import VARIANT
    flat = [c for p in points for c in p]
    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat)


# 铁律：一次工具调用 = 一个复合 COM 任务；任务内完成取文档/建样式/建图层/画图/取句柄，
# 只把纯数据（句柄字符串）传回调用方。活体 COM 对象禁止跨任务边界传递。

def _ensure_cn_style_core(doc) -> None:
    """D5：MCP_CN 样式幂等创建（gbenor+gbcbig），不动用户 Standard。"""
    try:
        doc.TextStyles.Item(CN_STYLE)
        return
    except Exception:
        pass
    try:
        st = doc.TextStyles.Add(CN_STYLE)
        st.fontFile = "gbenor.shx"
        st.BigFontFile = "gbcbig.shx"
    except Exception:
        pass  # 字体缺失时保留默认，文字仍创建


def _ensure_layer_core(doc, layer: str) -> None:
    try:
        doc.Layers.Item(layer)
    except Exception:
        doc.Layers.Add(layer)


def _create_one_core(doc, it: dict[str, Any]):
    """在 COM 线程上真正创建实体；前置校验已由纯层完成。"""
    kind = it["kind"]
    if it.get("layer"):
        _ensure_layer_core(doc, it["layer"])
    if kind == "line":
        ent = doc.ModelSpace.AddLine(
            _variant_pt(float(it["x1"]), float(it["y1"])),
            _variant_pt(float(it["x2"]), float(it["y2"])))
    elif kind in ("circle", "arc"):
        r = float(it.get("radius", it.get("r",
            float(it.get("diameter", -1)) / 2 if "diameter" in it else -1)))
        if kind == "circle":
            ent = doc.ModelSpace.AddCircle(
                _variant_pt(float(it.get("cx", 0)), float(it.get("cy", 0))), r)
        else:
            ent = doc.ModelSpace.AddArc(
                _variant_pt(float(it.get("cx", 0)), float(it.get("cy", 0))), r,
                math.radians(float(it.get("start_angle", 0))),
                math.radians(float(it.get("end_angle", 360))))
    elif kind == "polyline":
        pts = [[float(p[0]), float(p[1])] for p in it["points"]]
        ent = doc.ModelSpace.AddLightWeightPolyline(_variant_flat(pts))
        if it.get("closed"):
            ent.Closed = True
    elif kind == "rectangle":
        x = float(it.get("x", 0)); y = float(it.get("y", 0))
        w = float(it.get("width", it.get("w", -1)))
        h = float(it.get("height", it.get("h", -1)))
        ent = doc.ModelSpace.AddLightWeightPolyline(
            _variant_flat([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]))
        ent.Closed = True
    elif kind == "text":
        _ensure_cn_style_core(doc)
        ent = doc.ModelSpace.AddText(str(it["text"]),
                                     _variant_pt(float(it["x"]), float(it["y"])),
                                     float(it.get("height", 3.5)))
        ent.StyleName = CN_STYLE
    else:
        raise ParamError(f"未知 kind={kind}")
    if it.get("layer"):
        ent.Layer = it["layer"]
    return str(ent.Handle)


def _get_doc(app):
    try:
        return app.ActiveDocument
    except Exception as e:  # Start 页无文档等场景
        raise SessionError(NO_DOCUMENT, "AutoCAD 无活动文档") from e


# --------------------------------------------------------------- 编排（工具层调）
_TOOL_PREFIX = "cad_draw_"


def create_single(session: AutoCADSession, journal, it: dict[str, Any]) -> dict:
    """单体工具编排：校验(纯) → 单复合任务 → 记账。"""
    try:
        validate_item(it)
    except ParamError as e:
        return fail(INVALID_PARAM, str(e))
    try:
        handle = session.execute(lambda app: _create_one_core(_get_doc(app), it))
    except SessionError as e:
        return fail(e.code, e.message)
    journal.record(_TOOL_PREFIX + it["kind"], [handle])
    return ok("已绘制", handles=[handle])


def create_batch(session: AutoCADSession, journal,
                 items: list[dict[str, Any]]) -> dict:
    """尽力而为批量（Q2）：整批=一个撤销单元；全败时返回首个具体错误。

    注意：重连重试发生在整个批任务的边界上（session.execute），
    任务内部逐项失败不会触发整批重放。
    """
    if not isinstance(items, list) or not items:
        return fail(INVALID_PARAM, "items 必须是非空数组")
    if len(items) > MAX_BATCH:
        return fail(INVALID_PARAM, f"items 超过上限 {MAX_BATCH}")

    norm: list[tuple[int, dict]] = []
    results: list[dict] = []
    for idx, raw in enumerate(items):
        it = raw if isinstance(raw, dict) else {"kind": str(raw)}
        try:
            validate_item(it)
            norm.append((idx, it))
        except ParamError as e:
            results.append({"index": idx, "ok": False,
                            "error_code": INVALID_PARAM, "reason": str(e)})

    handles: list[str] = []
    if norm:
        def job(app):
            doc = _get_doc(app)
            out = []
            for idx, it in norm:
                try:
                    h = _create_one_core(doc, it)
                    out.append({"index": idx, "ok": True,
                                "kind": it.get("kind"), "handle": h})
                except ParamError as e:
                    out.append({"index": idx, "ok": False,
                                "error_code": INVALID_PARAM, "reason": str(e)})
                except Exception as e:  # noqa: BLE001 - 单项失败不拖垮整批
                    out.append({"index": idx, "ok": False,
                                "error_code": COM_FAILURE, "reason": str(e)})
            return out
        try:
            results.extend(session.execute(job))
        except SessionError as e:
            return fail(e.code, e.message)

    for r in results:
        if r["ok"]:
            handles.append(r["handle"])
    created = sum(1 for r in results if r["ok"])
    failed = len(results) - created
    if handles:
        journal.record("cad_create_batch", handles)
    if failed == 0:
        return ok(f"成功创建 {created} 个图元", handles=handles,
                  data={"items": results})
    msg = f"批量完成：{created} 成功 / {failed} 失败"
    r = partial(handles, results, msg)
    if created == 0:
        bad = next((r for r in results if not r["ok"]), None)
        if bad:
            r["error"]["code"] = bad.get("error_code", PARTIAL)
            r["error"]["message"] = f"items[{bad['index']}] {bad.get('reason','')}"
    return r
