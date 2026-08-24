"""AutoCAD MCP 服务入口：FastMCP 装配层（薄），业务在兄弟模块。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # src/

from fastmcp import FastMCP  # noqa: E402

from cad_mcp.result import fail, ok  # noqa: E402
from cad_mcp.session import AutoCADSession, SessionError  # noqa: E402

mcp = FastMCP("autocad-mcp")
session = AutoCADSession()


def _guard(fn):
    """把 SessionError 统一转成契约错误形态的装饰器。"""
    from functools import wraps

    @wraps(fn)
    def wrapper(*a, **k):
        from cad_mcp.tools_meta import is_write_tool
        import time as _t
        name = fn.__name__
        t0 = _t.monotonic()
        if READ_ONLY and is_write_tool(name):
            return fail("READ_ONLY",
                        "服务以 --read-only 模式启动，变更类工具已禁用")
        try:
            r = fn(*a, **k)
            log.info("tool ok", extra={"tool": name, "duration_ms": int((_t.monotonic()-t0)*1000), "ok": True})
            return r
        except SessionError as e:
            import time as _t3
            log.warning("tool failed", extra={"tool": name, "ok": False,
                                              "code": e.code,
                                              "duration_ms": int((_t3.monotonic()-t0)*1000)})
            return fail(e.code, e.message)
    return wrapper


@mcp.tool()
@_guard
def cad_status() -> dict:
    """查询与 AutoCAD 的连接状态及当前文档信息。无参数。"""
    return {"ok": True, "message": "状态如下", "data": session.status()}


# ---------------- US1 绘图工具（契约 v1.1）----------------
from cad_mcp.drawing import create_single, create_batch  # noqa: E402
from cad_mcp.journal import OperationJournal  # noqa: E402

journal = OperationJournal()

from cad_mcp.logging_setup import setup as _setup_logging  # T024/D7+FR-17
# argv（零 env 约束不变）：--read-only / --verbose
READ_ONLY = "--read-only" in sys.argv
VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv
log = _setup_logging(VERBOSE)
# 预载 OpenCV（主线程）：规避 5.x 在 worker 线程首载时的 DLL 死锁；
# 同时禁其内部并行，避免与 anyio/COM 线程池互掐
try:
    import cv2 as _cv2_preload
    _cv2_preload.setNumThreads(0)
except Exception:
    pass


def _get_doc(app):
    from cad_mcp.session import SessionError, NO_DOCUMENT
    try:
        return app.ActiveDocument
    except Exception as e:
        raise SessionError(NO_DOCUMENT, "AutoCAD 无活动文档") from e


@mcp.tool()
@_guard
def cad_draw_line(x1: float, y1: float, x2: float, y2: float,
                  layer: str | None = None) -> dict:
    """画一条直线。参数为两端点世界坐标；可选图层名。"""
    return create_single(session, journal,
                         {"kind": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                          "layer": layer})


@mcp.tool()
@_guard
def cad_draw_circle(cx: float, cy: float, r: float,
                    layer: str | None = None) -> dict:
    """画圆。cx/cy 为圆心，r 为半径（必须>0）。"""
    return create_single(session, journal,
                         {"kind": "circle", "cx": cx, "cy": cy, "r": r, "layer": layer})


@mcp.tool()
@_guard
def cad_draw_arc(cx: float, cy: float, r: float, start_angle: float,
                 end_angle: float, layer: str | None = None) -> dict:
    """画弧。角度为度，从 start_angle 逆时针到 end_angle。"""
    return create_single(session, journal,
                         {"kind": "arc", "cx": cx, "cy": cy, "r": r,
                          "start_angle": start_angle, "end_angle": end_angle,
                          "layer": layer})


@mcp.tool()
@_guard
def cad_draw_polyline(points: list[list[float]], closed: bool = False,
                      layer: str | None = None) -> dict:
    """画多段线。points 为 [x,y] 点列；closed=True 时闭合（至少3点）。"""
    return create_single(session, journal,
                         {"kind": "polyline", "points": points,
                          "closed": closed, "layer": layer})


@mcp.tool()
@_guard
def cad_draw_rectangle(x: float, y: float, w: float, h: float,
                       layer: str | None = None) -> dict:
    """画矩形（单条闭合多段线）。x/y 为左下角，w/h 宽高。"""
    return create_single(session, journal,
                         {"kind": "rectangle", "x": x, "y": y, "w": w, "h": h,
                          "layer": layer})


@mcp.tool()
@_guard
def cad_draw_text(text: str, x: float, y: float, height: float = 3.5,
                  layer: str | None = None) -> dict:
    """写单行文字。默认字高 3.5mm、自动用支持中文的样式。"""
    return create_single(session, journal,
                         {"kind": "text", "text": text, "x": x, "y": y,
                          "height": height, "layer": layer})


@mcp.tool()
@_guard
def cad_create_batch(items: list[dict]) -> dict:
    """批量创建图元（尽力而为）：items 每项 {kind: line|circle|arc|polyline|rectangle|text, ...该类型参数}。
    部分失败不影响已成功项；整批计为一个撤销单元。"""
    return create_batch(session, journal, items)


# ---------------- US2 图层 / US3 查询 / US4 安全网 ----------------
import os as _os  # noqa: E402

from cad_mcp.layers import create_layer_core, list_layers_core  # noqa: E402
from cad_mcp.query import query_core, PAGE_DEFAULT, PAGE_MAX  # noqa: E402


@mcp.tool()
@_guard
def cad_create_layer(name: str, color: int | None = None,
                     linetype: str | None = None) -> dict:
    """创建图层（幂等）：已存在同名层时直接返回其信息。color 为 ACI 索引(1-255)。"""
    if not isinstance(name, str) or not (1 <= len(name.strip()) <= 255):
        return fail("INVALID_PARAM", "图层名必须是非空且 ≤255 字符的字符串")

    def job(app):
        doc = _get_doc(app)
        created = create_layer_core(doc, name.strip(), color, linetype)
        lay = doc.Layers.Item(name.strip())
        return {"created": created,
                "layer": {"name": str(lay.Name), "color": int(lay.Color),
                          "linetype": str(lay.Linetype), "on": bool(lay.LayerOn)}}
    try:
        out = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    except ValueError as e:
        return fail("INVALID_PARAM", f"颜色索引非法：{e}")
    msg = ("图层已存在" if not out["created"] else "图层已创建")
    return ok(msg, data=out)


@mcp.tool()
@_guard
def cad_list_layers() -> dict:
    """列出当前图纸全部图层。无参数。"""
    try:
        layers = session.execute(lambda app: list_layers_core(_get_doc(app)), write_safe=False)
    except SessionError as e:
        return fail(e.code, e.message)
    return ok(f"共 {len(layers)} 个图层", data={"layers": layers})


@mcp.tool()
@_guard
def cad_query_entities(page: int = 1, page_size: int = PAGE_DEFAULT) -> dict:
    """分页查询图纸实体清单。每项含句柄/类型/图层/几何摘要；首页性能见规格 SC-6。"""
    if page < 1:
        return fail("INVALID_PARAM", "page 必须 ≥ 1")
    if not (1 <= page_size <= PAGE_MAX):
        return fail("INVALID_PARAM", f"page_size 必须在 1..{PAGE_MAX}")
    try:
        data = session.execute(lambda app: query_core(_get_doc(app), page, page_size), write_safe=False)
    except SessionError as e:
        return fail(e.code, e.message)
    return ok(f"第 {page} 页，共 {data['total']} 个实体", data=data)


@mcp.tool()
@_guard
def cad_undo() -> dict:
    """单步撤销：回退最近一次成功绘制操作（Q1）。无可撤销时空手而归。"""
    taken = journal.take()
    if taken is None:
        return ok("无可撤销操作",
                  data={"removed_handles": [], "skipped_handles": []})
    tool, handles = taken

    def job(app):
        doc = _get_doc(app)
        removed, skipped = [], []
        for h in handles:
            try:
                ent = doc.HandleToObject(h)
                ent.Delete()
                removed.append(h)
            except Exception:
                skipped.append(h)  # 用户已手删：如实报告（Q1 决议）
        return {"removed_handles": removed, "skipped_handles": skipped}
    try:
        out = session.execute(job)
    except SessionError as e:
        journal.record(tool, handles)  # 撤销失败：把记账放回去，保持可重试
        return fail(e.code, e.message)
    return ok(f"已撤销 {tool}", data=out)


def _to_win_path(p: str) -> str:
    r"""/mnt/X/... → X:\...（其余原样返回）"""
    if p.startswith("/mnt/") and len(p) > 6:
        drive, rest = p[5], p[6:]
        return f"{drive.upper()}:{rest}"
    return p


@mcp.tool()
@_guard
def cad_save_dwg(path: str, overwrite: bool = False) -> dict:
    """另存为 DWG。路径已存在且未带 overwrite=true 时拒绝（FR-6 防静默覆盖）。
    支持 /mnt/X/... 形式自动转为 Windows 路径。"""
    win = _to_win_path(_os.path.expanduser(path))
    base = _os.path.basename(win).lower()
    dup = session.execute(lambda app: any(
        str(d.Name).lower() == base for d in app.Documents))
    if dup:
        return fail("PATH_IN_USE",
                    f"{base} 正被会话内打开的文档标签占用")
    if _os.path.exists(win) and not overwrite:
        return fail("SAVE_CONFLICT", f"目标已存在：{win}")
    try:
        session.execute(lambda app: _get_doc(app).SaveAs(win))
    except SessionError as e:
        return fail(e.code, e.message)
    except Exception as e:  # SaveAs 参数级错误（坏路径等）
        return fail("COM_FAILURE", f"保存失败：{e}")
    return ok("已保存", data={"saved_path": win})


# ================= v2.0 扩展（契约 v2.0，+21 工具）=================
from cad_mcp import dims as _dims  # noqa: E402
from cad_mcp import ops as _ops    # noqa: E402
from cad_mcp import vision as _vis # noqa: E402
from cad_mcp.generators import (   # noqa: E402
    bolt_items as _bolt_items,
    flange_items as _flange_items,
    gear_profile as _gear_profile,
)


@mcp.tool()
@_guard
def cad_dim_aligned(x1: float, y1: float, x2: float, y2: float,
                    ox: float, oy: float, text: str | None = None) -> dict:
    """对齐尺寸标注：两界址点 + 尺寸线偏移点；text 可覆盖默认值。"""
    return _dims.dim_aligned(session, x1, y1, x2, y2, ox, oy, text)


@mcp.tool()
@_guard
def cad_dim_diameter(handle: str, chord_x: float, chord_y: float,
                     leader_len: float = 5.0, text: str | None = None) -> dict:
    """直径标注（圆/弧）。chord 为圆周上引出点。"""
    return _dims.dim_diameter(session, handle, chord_x, chord_y, leader_len, text)


@mcp.tool()
@_guard
def cad_dim_radius(handle: str, chord_x: float, chord_y: float,
                   leader_len: float = 5.0, text: str | None = None) -> dict:
    """半径标注。"""
    return _dims.dim_radius(session, handle, chord_x, chord_y, leader_len, text)


@mcp.tool()
@_guard
def cad_hatch(handles: list[str], pattern: str = "ANSI31",
              scale: float = 1.0, angle_deg: float = 0.0) -> dict:
    """图案填充（需闭合边界实体句柄）。默认 ANSI31 剖面线。"""
    return _dims.hatch(session, handles, pattern, scale, angle_deg)


@mcp.tool()
@_guard
def cad_draw_mtext(text: str, x: float, y: float, width: float,
                   height: float = 3.5, layer: str | None = None) -> dict:
    """多行文字。"""
    return _dims.draw_mtext(session, text, x, y, width, height, layer)


@mcp.tool()
@_guard
def cad_send_command(command: str) -> dict:
    """逃生舱：向 AutoCAD 命令行发送任意命令或 AutoLISP 表达式。
    异步执行无返回值；请用查询类工具观察结果。"""
    return _ops.send_command(session, command)


@mcp.tool()
@_guard
def cad_get_entity(handle: str) -> dict:
    """按句柄查询单个实体详情（类型/图层/几何摘要）。"""
    return _ops.get_entity(session, handle)


@mcp.tool()
@_guard
def cad_delete_entities(handles: list[str]) -> dict:
    """按句柄批量删除实体；自动同步撤销日志。"""
    return _ops.delete_entities(session, journal, handles)


@mcp.tool()
@_guard
def cad_set_layer_props(name: str, color: int | None = None,
                        linetype: str | None = None, on: bool | None = None,
                        frozen: bool | None = None,
                        current: bool | None = None) -> dict:
    """修改图层属性（颜色/线型/开关/冻结/置当前），至少一个字段。"""
    return _ops.set_layer_props(session, name, color, linetype, on, frozen, current)


@mcp.tool()
@_guard
def cad_list_documents() -> dict:
    """列出全部打开文档及活动标记。"""
    return _ops.list_documents(session)


@mcp.tool()
@_guard
def cad_activate_document(name: str) -> dict:
    """切换活动文档。"""
    return _ops.activate_document(session, name)


@mcp.tool()
@_guard
def cad_list_blocks() -> dict:
    """列出已定义块名。"""
    return _ops.list_blocks(session)


@mcp.tool()
@_guard
def cad_insert_block(name: str, x: float, y: float, scale: float = 1.0,
                     rot_deg: float = 0.0, layer: str | None = None) -> dict:
    """插入块参照。"""
    return _ops.insert_block(session, name, x, y, scale, rot_deg, layer)


@mcp.tool()
@_guard
def cad_zoom(mode: str = "extents", x1: float | None = None,
             y1: float | None = None, x2: float | None = None,
             y2: float | None = None) -> dict:
    """视图缩放：extents 或 window(x1,y1,x2,y2)。截图前用。"""
    return _vis.zoom(session, mode, x1, y1, x2, y2)


@mcp.tool()
@_guard
def cad_export_screenshot(path: str) -> dict:
    """★视觉闭环：把 AutoCAD 当前窗口截屏存为 PNG 并返回路径——agent 可自看效果再迭代。"""
    return _vis.export_screenshot(session, _to_win_path(path))


@mcp.tool()
@_guard
def gen_bolt(d: int = 12, L: int = 50) -> dict:
    """★参数化生成：GB/T 5782 六角头螺栓双视图。d∈{8,10,12,16,20}。整批一个撤销单元。"""
    try:
        out = _bolt_items(d=d, L=L)
    except Exception as e:
        return fail("INVALID_PARAM", str(e))
    r = create_batch(session, journal, out["items"])
    r.setdefault("data", {})["bolt_meta"] = out["meta"]
    return r


@mcp.tool()
@_guard
def gen_flange(D: float = 200, K: float = 160, n: int = 8, L: float = 18,
               b: float = 20, d1: float = 128, A: float = 89, f: float = 2.0,
               scale: float = 0.5, origin_x: float = 100, origin_y: float = 120) -> dict:
    """★参数化生成：板式平焊法兰双视图（几何+中心线，标注请另行添加）。"""
    try:
        its = _flange_items(D=D, K=K, n=n, L=L, b=b, d1=d1, A=A, f=f,
                            scale=scale, origin=[origin_x, origin_y])
    except Exception as e:
        return fail("INVALID_PARAM", str(e))
    return create_batch(session, journal, its)


@mcp.tool()
@_guard
def gen_gear_spur(z: int = 20, module: float = 2.0, bore_r: float | None = None,
                  pressure_angle: float = 20.0,
                  x: float = 150, y: float = 120) -> dict:
    """★参数化生成：渐开线直齿外齿轮轮廓（近似折线）+ 可选内孔。"""
    try:
        g = _gear_profile(z=z, module=module, pressure_angle=pressure_angle)
        pts = [[px + x, py + y] for px, py in g["points"]]
        items = [{"kind": "polyline", "points": pts, "closed": True, "layer": "OUTLINE"}]
        if bore_r and bore_r > 0:
            items.append({"kind": "circle", "cx": x, "cy": y, "r": bore_r, "layer": "OUTLINE"})
        items.append({"kind": "line", "x1": x - g["meta"]["ra"] * 1.15,
                      "y1": y, "x2": x + g["meta"]["ra"] * 1.15,
                      "y2": y, "layer": "CENTER"})
        items.append({"kind": "line", "x1": x, "y1": y - g["meta"]["ra"] * 1.15,
                      "x2": x, "y2": y + g["meta"]["ra"] * 1.15, "layer": "CENTER"})
        meta = g["meta"]
    except Exception as e:
        return fail("INVALID_PARAM", str(e))
    r = create_batch(session, journal, items)
    r.setdefault("data", {})
    r["data"]["gear_meta"] = meta
    return r


@mcp.tool()
@_guard
def cad_array_polar(handle: str, count: int, fill_deg: float = 360.0,
                    cx: float = 0.0, cy: float = 0.0) -> dict:
    """环形阵列实体（原体保留，返回新增句柄；整组一个撤销单元）。"""
    return _ops.array_polar(session, journal, handle, count, fill_deg, cx, cy)


@mcp.tool()
@_guard
def cad_array_rect(handle: str, rows: int, cols: int,
                   row_dx: float, col_dy: float) -> dict:
    """矩形阵列实体。row_dx/col_dy 为行列间距（可负）。"""
    return _ops.array_rect(session, journal, handle, rows, cols, row_dx, col_dy)


# ================= v2.1 流水线（002-nlp-plan-pipeline，+8 工具）=================
from cad_mcp.parser import parse_text as _parse_text          # noqa: E402
from cad_mcp.planner import (                                  # noqa: E402
    plan_from_parse as _plan_from_parse,
    validate_plan as _validate_plan,
    execute_plan as _execute_plan,
)
from cad_mcp.sheet import init_sheet as _init_sheet            # noqa: E402
from cad_mcp.imagegeo import import_geometry as _import_geom   # noqa: E402
from cad_mcp.dwgscan import scan_dwg as _scan_dwg              # noqa: E402
from cad_mcp.rules_engine import list_rulesets as _list_rulesets  # noqa: E402


@mcp.tool()
@_guard
def cad_parse_text(text: str) -> dict:
    """确定性中英文尺寸解析兜底（零幻觉）：WxH/Φ/R/角度/单位/意图。提不出就如实报 missing。"""
    return ok("解析完成", data=_parse_text(text))


@mcp.tool()
@_guard
def cad_plan(text: str, origin_x: float = 0.0, origin_y: float = 0.0,
             scale: float = 1.0) -> dict:
    """从自然语言生成结构化图纸计划（纯数据不落图）：含 assumptions/warnings。"""
    try:
        pr = _parse_text(text)
        plan = _plan_from_parse(pr, origin=[origin_x, origin_y], scale=scale)
    except Exception as e:
        return fail("INVALID_PARAM", f"规划失败：{e}")
    return ok(f"计划含 {len(plan['entities'])} 个实体", data={"plan": plan})


@mcp.tool()
@_guard
def cad_validate_plan(plan: dict, ruleset: str | None = None) -> dict:
    """四类校验（完整性/一致性/可执行性/专业性）；可叠加行业规则包。"""
    try:
        issues = _validate_plan(plan or {}, ruleset)
    except Exception as e:
        return fail("INVALID_PARAM", f"校验器异常：{e}")
    errors = [i for i in issues if i["severity"] == "error"]
    return ok("校验通过" if not errors else f"{len(errors)} 个 error",
              data={"pass": not errors, "issues": issues})


@mcp.tool()
@_guard
def cad_execute_plan(plan: dict, ruleset: str | None = None) -> dict:
    """执行已校验计划（整批一个撤销单元）。存在 error 级 issue 时拒绝并内联返回清单；
    assumptions/warnings 随结果透传给 agent。"""
    return _execute_plan(session, journal, plan or {}, ruleset)


@mcp.tool()
@_guard
def cad_init_sheet(template: str = "gb-mech", size: str = "A4",
                   title_block: bool = True,
                   origin_x: float = 10.0, origin_y: float = 10.0) -> dict:
    """一键初始化标准制图环境：五层模板（gb-mech）+ 图框 + 简化标题栏；幂等。"""
    return _init_sheet(session, template, size, title_block, [origin_x, origin_y])


@mcp.tool()
@_guard
def cad_import_image_geometry(path: str, scale: float = 1.0,
                              origin_x: float = 0.0, origin_y: float = 0.0,
                              min_confidence: float = 0.5) -> dict:
    """图片→几何（OpenCV 检测 line/circle/rect）。返回可直接喂给 cad_create_batch 的 items。
    未装 opencv 时返回 MISSING_DEP 安装指引。"""
    return _import_geom(_to_win_path(path), scale, [origin_x, origin_y], min_confidence)


@mcp.tool()
@_guard
def cad_scan_dwg(path: str, sample: int = 20) -> dict:
    """扫描已有 DWG 文件（实体计数/类型分布/图层/抽样摘要），即开即关不留标签。"""
    return _scan_dwg(session, _to_win_path(path), int(sample))


@mcp.tool()
@_guard
def cad_dim_rotated(x1: float, y1: float, x2: float, y2: float,
                    dimline_x: float, dimline_y: float,
                    rot_deg: float = 0.0, text: str | None = None,
                    layer: str | None = None) -> dict:
    """真 RotatedDimension 线性标注（水平 0°/垂直 90°/任意角）。"""
    return _dims.dim_rotated(session, x1, y1, x2, y2, dimline_x, dimline_y,
                             rot_deg, text, layer)


@mcp.tool()
@_guard
def cad_tolerance_frame(location_x: float, location_y: float, text: str,
                        height: float | None = None,
                        layer: str | None = None) -> dict:
    """真 AcDbFcf 形位公差框格。text 支持 GDT 控制码。"""
    return _dims.tolerance_frame(session, location_x, location_y,
                                 text, height, layer)


@mcp.tool()
@_guard
def cad_leader(points: list[list[float]], annotation_text: str | None = None,
               layer: str | None = None, annotation_x: float | None = None,
               annotation_y: float | None = None,
               ann_height: float = 3.5) -> dict:
    """真 AcDbLeader 引线（≥2 点），可选附注文字。"""
    pts = [[float(px), float(py)] for px, py in points]
    return _dims.leader_obj(session, pts, annotation_text, layer,
                            annotation_x, annotation_y, ann_height)


@mcp.tool()
@_guard
def cad_list_rulesets() -> dict:
    """列出可用行业规则包（AI 测评执行末端）。"""
    packs = _list_rulesets()
    return ok(f"共 {len(packs)} 个规则包", data={"rulesets": packs})


def main() -> None:
    log.info("autocad-mcp starting (stdio)")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
