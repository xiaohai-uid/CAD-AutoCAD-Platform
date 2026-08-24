"""图纸查询：分页纯函数（可离线测）+ 实体枚举与几何摘要（COM 任务内执行）。"""
from __future__ import annotations
import math
from typing import Any

PAGE_DEFAULT, PAGE_MAX = 100, 500


def paginate(total: int, page: int, page_size: int) -> tuple[int, int]:
    """返回 [start, end) 切片窗口；越界页给空窗口，绝不抛错。"""
    start = min(max(page - 1, 0) * page_size, total)
    end = min(start + page_size, total)
    return start, end


def kind_of(object_name: str) -> str:
    return {
        "AcDbLine": "LINE", "AcDbCircle": "CIRCLE", "AcDbArc": "ARC",
        "AcDbPolyline": "LWPOLYLINE", "AcDbText": "TEXT",
    }.get(object_name, object_name)


def _pt(v) -> list[float]:
    return [round(float(c), 6) for c in tuple(v)[:2]]


def _geometry(e, kind: str) -> dict[str, Any]:
    if kind == "LINE":
        return {"start": _pt(e.StartPoint), "end": _pt(e.EndPoint)}
    if kind == "CIRCLE":
        return {"center": _pt(e.Center), "radius": round(float(e.Radius), 6)}
    if kind == "ARC":
        return {"center": _pt(e.Center), "radius": round(float(e.Radius), 6),
                "start_angle": round(math.degrees(float(e.StartAngle)), 4),
                "end_angle": round(math.degrees(float(e.EndAngle)), 4)}
    if kind == "LWPOLYLINE":
        flat = list(tuple(e.Coordinates))
        pts = [[round(flat[i], 6), round(flat[i + 1], 6)] for i in range(0, len(flat), 2)]
        return {"points": pts, "closed": bool(e.Closed)}
    if kind == "TEXT":
        return {"text": str(e.TextString), "position": _pt(e.InsertionPoint),
                "height": round(float(e.Height), 6)}
    return {}


def query_core(doc, page: int, page_size: int) -> dict[str, Any]:
    """D8：轻量枚举定位窗口 → 仅当前页深读几何。整个函数在单个 COM 任务内跑。"""
    ms = doc.ModelSpace
    total = int(ms.Count)
    start, end = paginate(total, page, page_size)
    items: list[dict[str, Any]] = []
    for i in range(start, end):
        e = ms.Item(i)
        raw = str(e.ObjectName)
        kind = kind_of(raw)
        items.append({
            "handle": str(e.Handle), "type": kind, "layer": str(e.Layer),
            "geometry": _geometry(e, kind),
        })
    return {"total": total, "page": page, "page_size": page_size, "items": items}
