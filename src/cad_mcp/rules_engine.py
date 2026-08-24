"""行业规则包引擎：JSON 外置规则 → 通用检查分派（FR-15，AI 测评执行末端）。"""
from __future__ import annotations
import json
import os
from typing import Any

RULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules")


def list_rulesets() -> list[dict[str, Any]]:
    out = []
    if os.path.isdir(RULES_DIR):
        for fn in sorted(os.listdir(RULES_DIR)):
            if fn.endswith(".json"):
                try:
                    d = json.load(open(os.path.join(RULES_DIR, fn), encoding="utf-8"))
                    out.append({"id": d.get("id", fn[:-5]),
                                "description": d.get("description", ""),
                                "rule_count": len(d.get("rules", []))})
                except Exception:
                    continue
    return out


def load_ruleset(ruleset_id: str) -> dict | None:
    for fn in os.listdir(RULES_DIR) if os.path.isdir(RULES_DIR) else []:
        if fn.endswith(".json"):
            try:
                d = json.load(open(os.path.join(RULES_DIR, fn), encoding="utf-8"))
                if d.get("id") == ruleset_id:
                    return d
            except Exception:
                continue
    return None


# ---------------- 通用检查分派器：check 名 → fn(plan, params) -> [issue片段] ----------------
def _chk_required_layers(plan, p):
    names = {l.get("name") for l in (plan.get("layers") or [])}
    miss = [n for n in p.get("names", []) if n not in names]
    return [{"code_suffix": "missing_layers",
             "message": f"缺少规范图层: {miss}"}] if miss else []


def _chk_positive_params(plan, p):
    fields = p.get("fields", [])
    bad = []
    for i, e in enumerate(plan.get("entities") or []):
        pr = e.get("params") or {}
        for f in fields:
            v = pr.get(f)
            try:
                if v is not None and float(v) <= 0:
                    bad.append(f"entities[{i}].{f}={v}")
            except (TypeError, ValueError):
                pass
    return [{"code_suffix": "nonpositive", "message": "非正值字段: " + ", ".join(bad)}] if bad else []


def _chk_min_text_height(plan, p):
    mn = float(p.get("min", 2.5))
    small = []
    for i, t in enumerate(plan.get("texts") or []):
        try:
            if float(t.get("height", 3.5)) < mn:
                small.append(f"texts[{i}]")
        except (TypeError, ValueError):
            pass
    return [{"code_suffix": "small_text", "message": f"字高小于 {mn}: {', '.join(small)}"}] if small else []


def _chk_no_circle_without_centerlayer(plan, p):
    names = {l.get("name") for l in (plan.get("layers") or [])}
    has_circle = any(e.get("kind") == "circle" for e in (plan.get("entities") or []))
    if has_circle and plan.get("layers") is not None and \
            not any("中心" in n or "center" in str(n).lower() for n in names):
        return [{"code_suffix": "no_center_layer", "message": "存在圆但未定义中心线层"}]
    return []


def _chk_title_block_present(plan, p):
    kws = p.get("keywords", [])
    texts = " ".join(str(t.get("text", "")) for t in (plan.get("texts") or []))
    missing = [k for k in kws if k not in texts]
    return [{"code_suffix": "tb_missing", "message": f"标题栏缺少关键字: {missing}"}] if missing else []


CHECKS = {
    "required_layers": _chk_required_layers,
    "positive_params": _chk_positive_params,
    "min_text_height": _chk_min_text_height,
    "no_circle_without_centerlayer": _chk_no_circle_without_centerlayer,
    "title_block_present": _chk_title_block_present,
}


def apply_ruleset(plan: dict[str, Any], ruleset_id: str) -> list[dict[str, Any]]:
    """把规则包结果并入 issue 流（severity 沿用包定义）。"""
    pack = load_ruleset(ruleset_id)
    if pack is None:
        return [{"severity": "error", "category": "professional",
                 "code": "RULESET_NOT_FOUND",
                 "message": f"规则包 {ruleset_id!r} 不存在；用 cad_list_rulesets 查看"}]
    issues = []
    for rule in pack.get("rules", []):
        chk = CHECKS.get(rule.get("check"))
        if chk is None:
            continue
        for frag in chk(plan, rule.get("params", {})):
            issues.append({"severity": rule.get("severity", "warning"),
                           "category": "professional",
                           "code": f'{rule["code"]}/{frag["code_suffix"]}',
                           "message": frag["message"],
                           "ruleset": ruleset_id})
    return issues
