"""制图环境初始化：gb-mech 五层模板（继承前作 DEFAULT_LAYERS 命名）+ A4 图框标题栏。"""
from __future__ import annotations
from typing import Any

from .drawing import _get_doc, _variant_pt
from .result import fail, ok
from .session import AutoCADSession, SessionError

GB_MECH_LAYERS: list[tuple[str, int, str]] = [
    ("轮廓线", 7, "Continuous"),
    ("中心线", 1, "CENTER"),
    ("标注", 3, "Continuous"),
    ("填充", 8, "Continuous"),
    ("文字", 2, "Continuous"),
]
SIZES = {"A4": (297, 210), "A3": (420, 297)}
TB_MARK = "FLANGE-E2E|CAD-MCP-E2E"   # 标题栏防重绘标记（图号位）


def layers_to_create(existing: set[str]) -> list[tuple[str, int, str]]:
    return [(n, c, lt) for n, c, lt in GB_MECH_LAYERS if n not in existing]


def init_sheet(session: AutoCADSession, template: str = "gb-mech",
               size: str = "A4", title_block: bool = True,
               origin: list[float] | None = None,
               ensure_document: bool = True) -> dict:
    if template != "gb-mech":
        return fail("INVALID_PARAM", f"暂仅支持模板 gb-mech，得到 {template!r}")
    if size not in SIZES:
        return fail("INVALID_PARAM", f"size 仅支持 {sorted(SIZES)}")
    ox, oy = (origin or [10, 10])

    def job(app):
        if ensure_document:
            try:
                _ = app.ActiveDocument
            except Exception:
                app.Documents.Add()          # 开始页无文档时自动新建空白图
        doc = _get_doc(app)
        existing = {str(doc.Layers.Item(i).Name) for i in range(doc.Layers.Count)}
        to_make = layers_to_create(existing)
        created = []
        for n, c, lt in to_make:
            lay = doc.Layers.Add(n)
            lay.Color = c
            try:
                doc.Linetypes.Item(lt)
            except Exception:
                for f in ("acad.lin", "acadiso.lin"):
                    try:
                        doc.Linetypes.Load(lt, f); break
                    except Exception:
                        continue
            lay.Linetype = lt
            created.append(n)

        frame_handle = None
        tb_handles: list[str] = []
        w, h = SIZES[size]
        already = any(str(doc.ModelSpace.Item(i).ObjectName) == "AcDbText"
                      and "CAD-MCP-E2E" in str(getattr(doc.ModelSpace.Item(i), "TextString", ""))
                      for i in range(doc.ModelSpace.Count))
        if title_block and not already:
            ms = doc.ModelSpace
            from win32com.client import VARIANT
            import pythoncom
            def P(x, y): return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, 0.0])
            made = ms.AddPolyline(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                          [ox, oy, 0, ox + w, oy, 0,
                                           ox + w, oy + h, 0, ox, oy + h, 0]))
            made.Closed = True
            frame_handle = str(made.Handle)
            tx, ty = ox + w - 130, oy + 2
            ln = ms.AddLine(P(tx + 65, ty), P(tx + 65, ty + 26)); tb_handles.append(str(ln.Handle))
            ln2 = ms.AddLine(P(tx, ty + 13), P(tx + 130, ty + 13)); tb_handles.append(str(ln2.Handle))
            for txt, X, Y, HH in [("板式平焊法兰盘", tx + 6, ty + 15.5, 4.5),
                                   ("比例 1:1", tx + 70, ty + 15.5, 3.2),
                                   ("参照 GB/T 9119", tx + 4, ty + 1.5, 2.8),
                                   ("图号 CAD-MCP-E2E", tx + 68, ty + 1.5, 3.2)]:
                te = ms.AddText(txt, P(X, Y), HH)
                te.Layer = "文字"
                tb_handles.append(str(te.Handle))
        return {"layers_created": created, "frame_handle": frame_handle,
                "tb_handles": tb_handles}

    try:
        out = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    msg = (f"新建图层 {len(out['layers_created'])} 个"
           + ("；标题栏已存在跳过" if title_block and not out["tb_handles"] else ""))
    return ok(msg, data=out)
