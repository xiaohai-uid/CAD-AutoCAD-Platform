"""Plan 一等公民：parse→plan 构建、四类校验、execute 编排（FR-9/10/11）。"""
from __future__ import annotations
import math
from typing import Any

from .result import fail, ok
from .session import AutoCADSession, SessionError
from .drawing import _create_one_core, _get_doc, ParamError
from . import dims as _dims

COORD_LIMIT = 10 ** 6
DEFAULT_LEN = 50.0
VALID_DIM_TYPES = {"aligned", "linear", "diameter", "radius"}
KINDS = {"line", "circle", "arc", "polyline", "rectangle", "text"}


# ---------------------------------------------------------------- parse → Plan
def plan_from_parse(pr: dict[str, Any], origin: list[float] | None = None,
                    scale: float = 1.0) -> dict[str, Any]:
    """把 ParseResult 组装成完整 Plan：网格排布 + 假设/警告显式记录。"""
    ox, oy = (origin or [0, 0])
    entities: list[dict] = []
    assumptions: list[dict] = [{"field": "origin", "value": [ox, oy],
                                "reason": "未指定位置：默认从原点附近网格排布"}]
    warnings: list[str] = []

    if pr.get("unit", "mm") != "mm":
        assumptions.append({"field": "unit", "value": pr["unit"],
                            "reason": "非 mm 数值未换算，按原值绘制"})

    step = 0
    for e in pr.get("entities", []):
        kind = e["kind"]; p = dict(e.get("params", {}))
        if kind == "circle":
            if "diameter" in p:
                p["radius"] = p.pop("diameter") / 2 * scale
            else:
                p["radius"] = p.get("radius", 0) * scale
            p.setdefault("cx", ox + 60 + (step % 4) * 80)
            p.setdefault("cy", oy - (step // 4) * 70)
            step += 1
        elif kind == "rectangle":
            p["width"] = p.get("width", 0) * scale
            p["height"] = p.get("height", 0) * scale
            p.setdefault("x", ox); p.setdefault("y", oy)
        elif kind == "line":
            if {"x1", "y1", "x2", "y2"} <= set(p):
                for k in ("x1", "x2"):
                    p[k] = p[k] * scale + ox
                for k in ("y1", "y2"):
                    p[k] = p[k] * scale + oy
            elif "angle" in p:
                a = math.radians(float(p.pop("angle")))
                ln = DEFAULT_LEN
                p.update({"x1": ox, "y1": oy, "x2": ox + ln * math.cos(a),
                          "y2": oy + ln * math.sin(a)})
                warnings.append(f"角度线缺长度：默认 {ln:g}（angle={math.degrees(a):g}°）")
            else:
                warnings.append("线段参数不完整，已跳过该实体")
                continue
        entities.append({"kind": kind, "params": p})

    layers = sorted({e.get("layer", "OUTLINE") for e in entities})
    return {"layers": [{"name": n} for n in layers],
            "entities": entities, "dimensions": [], "texts": [],
            "assumptions": assumptions, "warnings": warnings,
            "unit": pr.get("unit", "mm"), "output_level": "sketch"}


# ---------------------------------------------------------------- 四类校验
def _issue(sev, cat, code, msg, loc=None):
    i = {"severity": sev, "category": cat, "code": code, "message": msg}
    if loc is not None:
        i["location"] = loc
    return i


def validate_plan(plan: dict[str, Any], ruleset: str | None = None) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    ents = plan.get("entities") or []
    layer_names = {l.get("name") for l in (plan.get("layers") or [])}

    # completeness
    if not ents:
        issues.append(_issue("error", "completeness", "COMPLETE_EMPTY",
                             "计划不含任何实体"))

    seen_ids = set()
    has_circle = False
    for idx, e in enumerate(ents):
        loc = f"entities[{idx}]"
        kind = e.get("kind")
        if eid := e.get("id"):
            if eid in seen_ids:
                issues.append(_issue("error", "consistency", "DUP_ID",
                                     f"{loc} id={eid!r} 重复", loc))
            seen_ids.add(eid)
        if kind not in KINDS:
            issues.append(_issue("error", "executability", "BAD_KIND",
                                 f"{loc} 未知类型 {kind!r}", loc))
            continue
        lay = e.get("layer")
        if lay and plan.get("layers") is not None and layer_names and lay not in layer_names:
            issues.append(_issue("error", "consistency", "LAYER_REF",
                                 f"{loc} 引用未定义图层 {lay!r}", loc))
        p = e.get("params") or {}
        try:
            if kind == "circle":
                has_circle = True
                r = float(p.get("radius", p.get("diameter", 1)) /
                          (2 if "radius" not in p and "diameter" in p else 1))
                if float(p.get("radius", p.get("diameter", -1))) <= 0:
                    raise ValueError("半径必须为正")
                cx, cy = float(p.get("cx", 0)), float(p.get("cy", 0))
            elif kind == "rectangle":
                w, h = float(p.get("width", -1)), float(p.get("height", -1))
                if w <= 0 or h <= 0:
                    raise ValueError("宽高必须为正")
                cx, cy = float(p.get("x", 0)), float(p.get("y", 0))
            else:
                cx = cy = 0
        except (TypeError, ValueError) as ex:
            issues.append(_issue("error", "executability", "BAD_PARAM",
                                 f"{loc} {ex}", loc))
            continue
        if any(abs(v) > COORD_LIMIT for v in (cx, cy)):
            issues.append(_issue("error", "executability", "OUT_OF_BOUNDS",
                                 f"{loc} 坐标超出 ±{COORD_LIMIT}", loc))

    # dimensions 校验
    for idx, d in enumerate((plan.get("dimensions") or [])):
        if d.get("type") not in VALID_DIM_TYPES:
            issues.append(_issue("error", "executability", "BAD_DIM_TYPE",
                                 f"dimensions[{idx}] 类型非法", f"dimensions[{idx}]"))

    # professional 建议
    if has_circle and plan.get("layers") is not None and \
            "CENTER" not in layer_names and len(layer_names) > 0:
        issues.append(_issue("warning", "professional", "NO_CENTER_LAYER",
                             "存在圆但未定义中心线层，建议补充 CENTER 层"))
    for idx, t in enumerate(plan.get("texts") or []):
        if float(t.get("height", 3.5)) < 1.5:
            issues.append(_issue("warning", "professional", "SMALL_TEXT",
                                 f"texts[{idx}] 字高过小(<1.5)", f"texts[{idx}]"))
    if ruleset:
        from .rules_engine import apply_ruleset
        issues.extend(apply_ruleset(plan, ruleset))
    return issues


# ---------------------------------------------------------------- 执行编排
def execute_plan(session: AutoCADSession, journal, plan: dict[str, Any],
                 ruleset: str | None = None) -> dict:
    issues = validate_plan(plan, ruleset)
    errors = [i for i in issues if i["severity"] == "error"]
    if errors:
        r = fail("VALIDATION_FAILED",
                 f"计划校验未通过：{len(errors)} 个 error / "
                 f"{len(issues) - len(errors)} 个 warning")
        r["data"] = {"issues": issues}
        return r

    def job(app):
        doc = _get_doc(app)
        import traceback as _tb
        made = []
        for idx, e in enumerate(plan.get("entities") or []):
            it = {"kind": e["kind"], **(e.get("params") or {})}
            if e.get("layer"):
                it["layer"] = e["layer"]
            try:
                h = _create_one_core(doc, it)
            except Exception as ex:
                tb = _tb.format_exc(limit=2)
                raise RuntimeError(f"[entity {idx} kind={e['kind']}] "
                                   f"{type(ex).__name__}: {ex} :: {tb}") from None
            made.append(str(h))
        dim_handles = []
        for d in (plan.get("dimensions") or []):
            dt = d.get("type")
            p = d.get("params") or {}
            if dt == "aligned":
                dd = doc.ModelSpace.AddDimAligned(
                    _variant_pt(p["x1"], p["y1"]), _variant_pt(p["x2"], p["y2"]),
                    _variant_pt(p.get("ox", p["x1"]), p.get("oy", p["y1"])))
                if d.get("text"):
                    dd.TextOverride = d["text"]
                dim_handles.append(str(dd.Handle))
        for t in (plan.get("texts") or []):
            from .drawing import _variant_pt as _P
            te = doc.ModelSpace.AddText(str(t["text"]), _P(float(t["x"]), float(t["y"])),
                                        float(t.get("height", 3.5)))
            if t.get("layer"):
                te.Layer = t["layer"]
            dim_handles.append(str(te.Handle))
        return made, dim_handles

    try:
        handles, extra_handles = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    except ParamError as e:
        return fail("INVALID_PARAM", str(e))
    journal.record("cad_execute_plan", handles + extra_handles)

    from .drawing import CN_STYLE
    data = {"entity_handles": handles, "annotation_handles": extra_handles}
    if plan.get("assumptions"):
        data["assumptions"] = plan["assumptions"]
    if plan.get("warnings"):
        data["warnings"] = plan["warnings"]
    warn_issues = [i for i in issues if i["severity"] == "warning"]
    if warn_issues:
        data["professional_warnings"] = warn_issues
    return ok(f"计划执行完成：{len(handles)} 实体 + {len(extra_handles)} 注释", data=data)
