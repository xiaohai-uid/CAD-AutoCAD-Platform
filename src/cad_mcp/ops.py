"""实体/图层/文档/块/命令行逃生舱/阵列。"""
from __future__ import annotations
import math
from typing import Any

from .drawing import ParamError, _variant_pt, _get_doc, validate_item, create_batch
from .query import kind_of, _geometry
from .result import fail, ok
from .session import AutoCADSession, SessionError


def send_command(session, command: str) -> dict:
    """fire-and-forget：向命令行发送任意命令/AutoLISP；结果用查询工具观察。"""
    if not command.strip():
        return fail("INVALID_PARAM", "command 不能为空")

    def job(app):
        doc = _get_doc(app)
        doc.SendCommand(str(command).rstrip() + "\n")
        return True
    try:
        session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    return ok("命令已发送（异步执行，请用查询工具确认结果）")


def get_entity(session, handle: str) -> dict:
    def job(app):
        doc = _get_doc(app)
        e = doc.HandleToObject(str(handle))
        raw = str(e.ObjectName)
        k = kind_of(raw)
        return {"handle": str(e.Handle), "type": k, "layer": str(e.Layer),
                "geometry": _geometry(e, k)}
    try:
        data = session.execute(job, write_safe=False)
    except SessionError as e:
        return fail(e.code, e.message)
    except Exception as e:
        return fail("INVALID_PARAM", f"句柄不存在或不可访问：{e}")
    return ok("实体详情", data=data)


def delete_entities(session, journal, handles) -> dict:
    if not isinstance(handles, list) or not handles:
        return fail("INVALID_PARAM", "handles 必须是非空数组")

    def job(app):
        doc = _get_doc(app)
        removed, skipped = [], []
        for h in handles:
            try:
                doc.HandleToObject(str(h)).Delete()
                removed.append(str(h))
            except Exception:
                skipped.append(str(h))
        return {"removed": removed, "skipped": skipped}
    try:
        out = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    removed = set(out["removed"])
    slot = journal.peek()                       # 同步撤销日志
    if slot:
        tool, hs = slot
        kept = [h for h in hs if h not in removed]
        if kept != hs:
            journal.record(tool, kept)
    return ok(f"删除 {len(out['removed'])} 个，跳过 {len(out['skipped'])} 个", data=out)


def set_layer_props(session, name, color=None, linetype=None,
                    on=None, frozen=None, current=None) -> dict:
    if not color and not linetype and on is None and frozen is None and current is None:
        return fail("INVALID_PARAM", "至少提供一个可变字段")
    def job(app):
        doc = _get_doc(app)
        try:
            lay = doc.Layers.Item(str(name))
        except Exception:
            return {"err": "NO_LAYER"}
        if color is not None:
            lay.Color = int(color)
        if linetype is not None:
            try:
                doc.Linetypes.Item(linetype)
            except Exception:
                for f in ("acad.lin", "acadiso.lin"):
                    try:
                        doc.Linetypes.Load(linetype, f); break
                    except Exception:
                        continue
            lay.Linetype = str(linetype)
        if on is not None:
            lay.LayerOn = bool(on)
        if frozen is not None:
            lay.Freeze = bool(frozen)
        if current:
            doc.ActiveLayer = lay
        return {"name": str(lay.Name), "color": int(lay.Color),
                "linetype": str(lay.Linetype), "on": bool(lay.LayerOn),
                "frozen": bool(lay.Freeze)}
    try:
        out = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    if "err" in out:
        return fail("INVALID_PARAM", f"图层 {name} 不存在")
    return ok("图层属性已更新", data={"layer": out})


def list_documents(session) -> dict:
    def job(app):
        act = str(app.ActiveDocument.Name)
        docs = [{"name": str(d.Name), "active": str(d.Name) == act}
                for d in app.Documents]
        return docs
    try:
        docs = session.execute(job, write_safe=False)
    except SessionError as e:
        return fail(e.code, e.message)
    return ok(f"共 {len(docs)} 个文档", data={"docs": docs})


def activate_document(session, name: str) -> dict:
    def job(app):
        app.ActiveDocument = app.Documents.Item(str(name))
        return str(app.ActiveDocument.Name)
    try:
        act = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    except Exception as e:
        return fail("INVALID_PARAM", f"文档不存在：{e}")
    return ok(f"已切换到 {act}", data={"active": act})


def list_blocks(session) -> dict:
    def job(app):
        doc = _get_doc(app)
        return [str(b.Name) for b in doc.Blocks if not b.Name.startswith("*")]
    try:
        blocks = session.execute(job, write_safe=False)
    except SessionError as e:
        return fail(e.code, e.message)
    return ok(f"共 {len(blocks)} 个块", data={"blocks": blocks})


def insert_block(session, name, x, y, scale=1.0, rot_deg=0.0, layer=None) -> dict:
    def job(app):
        doc = _get_doc(app)
        e = doc.ModelSpace.InsertBlock(_variant_pt(x, y), str(name),
                                       float(scale), float(scale), float(scale),
                                       math.radians(float(rot_deg)))
        if layer:
            e.Layer = layer
        return str(e.Handle)
    try:
        h = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    except Exception as e:
        return fail("INVALID_PARAM", f"插入失败（块名不存在？）：{e}")
    return ok("块已插入", handles=[h])


def array_polar(session, journal, handle, count, fill_deg=360.0, cx=0.0, cy=0.0) -> dict:
    if int(count) < 2:
        return fail("INVALID_PARAM", "count 必须 ≥ 2")
    def job(app):
        doc = _get_doc(app)
        ent = doc.HandleToObject(str(handle))
        arr = ent.ArrayPolar(int(count), math.radians(float(fill_deg)), _variant_pt(cx, cy))
        return [str(o.Handle) for o in tuple(arr)]
    try:
        new_handles = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    journal.record("cad_array_polar", new_handles)
    return ok(f"环形阵列完成，新增 {len(new_handles)} 个", handles=new_handles)


def array_rect(session, journal, handle, rows, cols, row_dx, col_dy) -> dict:
    if int(rows) < 1 or int(cols) < 1 or (int(rows) == 1 and int(cols) == 1):
        return fail("INVALID_PARAM", "rows/cols 至少一个方向 ≥ 2")
    if row_dx == 0 and col_dy == 0:
        return fail("INVALID_PARAM", "行列间距不能同时为 0")
    def job(app):
        doc = _get_doc(app)
        ent = doc.HandleToObject(str(handle))
        arr = ent.ArrayRectangular(int(rows), int(cols), 1,
                                   float(row_dx), float(col_dy), 0.0)
        return [str(o.Handle) for o in tuple(arr)]
    try:
        new_handles = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    journal.record("cad_array_rect", new_handles)
    return ok(f"矩形阵列完成，新增 {len(new_handles)} 个", handles=new_handles)
