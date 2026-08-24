"""确定性中英文尺寸解析器（FR-8）。
正则库移植自创始人前作 CAD-AutoCAD-Platform IntakeEngine/CADPlanEngine（MIT）。"""
from __future__ import annotations
import re
from typing import Any

_NUM = r"-?\d+(?:\.\d+)?"

RE_RECT = re.compile(rf"(?P<w>{_NUM})\s*[xX×]\s*(?P<h>{_NUM})")
RE_PHI = re.compile(rf"(?:[Φφϕ]|phi|直径\s*[为是]?|dia(?:meter)?)\s*(?P<d>{_NUM})", re.IGNORECASE)
RE_RAD = re.compile(rf"(?:半径\s*R?|radius\s*R?|\bR\b)\s*(?P<r>{_NUM})", re.IGNORECASE)
RE_ANG = re.compile(rf"(?P<a>{_NUM})\s*[°°]")
RE_LINE_PTS = re.compile(
    rf"line\s+(?:from\s+)?\(?\s*(?P<x1>{_NUM})\s*[,，]\s*(?P<y1>{_NUM})\s*\)?"
    rf"\s*(?:to|到)\s*\(?\s*(?P<x2>{_NUM})\s*[,，]\s*(?P<y2>{_NUM})\s*\)?", re.IGNORECASE)
RE_UNIT = {
    "mm": re.compile(r"\bmm\b|毫米", re.I),
    "cm": re.compile(r"\bcm\b|厘米", re.I),
    "inch": re.compile(r"\binch(?:es)?\b|英寸|\b\"", re.I),
}
RE_INTENT_CREATE = re.compile(r"画|绘|创建|添加|圆|矩形|孔|槽|线|齿轮|法兰|螺栓|draw|create|make|add", re.I)
RE_INTENT_EDIT = re.compile(r"修改|编辑|移动|旋转|删除|edit|modify|change|delete|move", re.I)


def parse_text(text: str) -> dict[str, Any]:
    """确定性提取：绝不编造；提不出的如实进 missing。"""
    t = str(text)
    entities: list[dict[str, Any]] = []
    consumed_spans: list[tuple[int, int]] = []

    def free(m: re.Match) -> bool:
        s, e = m.span()
        return not any(s < ce and e > cs for cs, ce in consumed_spans)

    # 线段（带端点）
    for m in RE_LINE_PTS.finditer(t):
        p = {k: float(v) for k, v in m.groupdict().items()}
        entities.append({"kind": "line", "params": p})
        consumed_spans.append(m.span())

    # 矩形 WxH
    for m in RE_RECT.finditer(t):
        if not free(m):
            continue
        p = {"width": float(m.group("w")), "height": float(m.group("h"))}
        entities.append({"kind": "rectangle", "params": p})
        consumed_spans.append(m.span())

    # 直径圆
    for m in RE_PHI.finditer(t):
        p = {"diameter": float(m.group("d"))}
        entities.append({"kind": "circle", "params": p})
        consumed_spans.append(m.span())

    # 半径圆（跳过已被直径消费的片段）
    for m in RE_RAD.finditer(t):
        if not free(m):
            continue
        p = {"radius": float(m.group("r"))}
        entities.append({"kind": "circle", "params": p})
        consumed_spans.append(m.span())

    # 角度线（无长度 → 仅记录角度，warning 由上层给）
    for m in RE_ANG.finditer(t):
        if not free(m):
            continue
        a = float(m.group("a"))
        if 0 <= a <= 360:
            entities.append({"kind": "line", "params": {"angle": a}})
            consumed_spans.append(m.span())

    unit = "mm"
    for u, rx in RE_UNIT.items():
        if rx.search(t):
            unit = u
            break

    if RE_INTENT_EDIT.search(t):
        intent = "edit"
    elif RE_INTENT_CREATE.search(t) or entities:
        intent = "create"
    else:
        intent = "unknown"

    missing = []
    if not entities:
        missing.append("dimensions")
    if intent == "unknown":
        missing.append("intent")

    return {"intent": intent, "entities": entities,
            "unit": unit, "missing": missing, "text": t}
