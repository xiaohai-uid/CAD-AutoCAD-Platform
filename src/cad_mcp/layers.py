"""图层领域层：幂等创建（US2）+ 线型回退加载。"""
from __future__ import annotations
from typing import Any

LINETYPE_FILES = ("acad.lin", "acadiso.lin")


class ParamError(Exception):
    pass


def create_layer_core(doc, name: str, color: int | None = None,
                      linetype: str | None = None) -> bool:
    """幂等：已存在返回 False；否则创建并应用属性，返回 True。

    线型未加载时依次尝试 LINETYPE_FILES；全部失败抛 ParamError（不残留半建图层）。
    """
    try:
        doc.Layers.Item(name)
        return False  # 幂等：存在即成功且 created=False
    except Exception:
        pass

    if linetype is not None:
        loaded = False
        try:
            doc.Linetypes.Item(linetype)
            loaded = True
        except Exception:
            for f in LINETYPE_FILES:
                try:
                    doc.Linetypes.Load(linetype, f)
                    loaded = True
                    break
                except Exception:
                    continue
        if not loaded:
            raise ParamError(f"线型 {linetype!r} 无法从 {LINETYPE_FILES} 加载")

    lay = doc.Layers.Add(name)
    if color is not None:
        lay.Color = int(color)
    if linetype is not None:
        lay.Linetype = linetype
    return True


def list_layers_core(doc) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i in range(doc.Layers.Count):
        L = doc.Layers.Item(i)
        out.append({
            "name": L.Name,
            "color": int(L.Color),
            "linetype": L.Linetype,
            "on": bool(L.LayerOn),
        })
    return out
