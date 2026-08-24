"""无人值守真机冒烟套件（FR-18）：六检查 + PASS/FAIL 表 + 非零退出码。

用法：python -m cad_mcp.smoke_suite [--json]
前置：AutoCAD 已启动；Windows Python 依赖已装。
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")


def _extract(res) -> dict:
    sc = getattr(res, "structuredContent", None)
    if isinstance(sc, dict):
        return sc
    for c in res.content:
        t = getattr(c, "text", None)
        if t:
            try:
                return json.loads(t)
            except Exception:
                pass
    return {"ok": False, "error": {"code": "NO_JSON", "message": str(res)[:120]}}


async def _run_checks() -> list[tuple[str, bool, str]]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    results: list[tuple[str, bool, str]] = []

    async with stdio_client(StdioServerParameters(command=sys.executable, args=[SERVER])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()

            async def call(name, args=None) -> dict:
                return _extract(await s.call_tool(name, args or {}))

            def rec(name, ok, detail=""):
                results.append((name, bool(ok), str(detail)[:90]))
                print(f"  [{'PASS' if ok else 'FAIL'}] {name:<24} {detail}"[:110],
                      flush=True)

            # 1 附着与状态（失败则后续无意义）
            try:
                st = (await call("cad_status")).get("data") or {}
                attached = bool(st.get("attached"))
                rec("attach_status", attached,
                    f"doc={st.get('doc_name')} entities={st.get('entity_count')}")
            except Exception as e:                               # noqa: BLE001
                rec("attach_status", False, str(e)[:80])
                return results
            if not attached:
                return results
            # 预置：确保存在活动文档（开始页场景）
            await call("cad_init_sheet")
            base = st.get("entity_count") or 0

            # 2 绘制撤销往返（净零）
            try:
                d = await call("cad_draw_circle", {"cx": 99999, "cy": 5, "r": 2})
                h = (d.get("handles") or [None])[0]
                u = await call("cad_undo")
                removed = (u.get("data") or {}).get("removed_handles", [])
                rec("draw_undo_roundtrip", d.get("ok") is True and h in removed,
                    f"handle={h}")
            except Exception as e:                               # noqa: BLE001
                rec("draw_undo_roundtrip", False, str(e)[:80])

            # 3 批量计数差（+5 后撤销；基准取批量前即时计数）
            try:
                pre = ((await call("cad_status")).get("data") or {}).get("entity_count") or 0
                b = await call("cad_create_batch", {"items": [
                    {"kind": "circle", "cx": 99990 + i * 7, "cy": 15, "r": 1.5}
                    for i in range(5)]})
                n_new = len(b.get("handles", []))
                st2 = (await call("cad_status")).get("data") or {}
                delta_ok = ((st2.get("entity_count") or 0) - pre) == 5
                await call("cad_undo")
                rec("batch_count_delta",
                    b.get("ok") is True and n_new == 5 and delta_ok,
                    f"+{n_new} delta_ok={delta_ok}")
            except Exception as e:                               # noqa: BLE001
                rec("batch_count_delta", False, str(e)[:80])

            # 4 初始化幂等
            try:
                i1 = await call("cad_init_sheet")
                i2 = await call("cad_init_sheet")
                c1 = len((i1.get("data") or {}).get("layers_created", []))
                c2 = len((i2.get("data") or {}).get("layers_created", []))
                rec("init_sheet_idempotent",
                    i1.get("ok") is True and i2.get("ok") is True and c2 == 0,
                    f"first={c1} second={c2}")
            except Exception as e:                               # noqa: BLE001
                rec("init_sheet_idempotent", False, str(e)[:80])

            # 5 分页查询
            try:
                q = await call("cad_query_entities", {"page": 1, "page_size": 10})
                rec("paged_query", q.get("ok") is True,
                    f"total={(q.get('data') or {}).get('total')}")
            except Exception as e:                               # noqa: BLE001
                rec("paged_query", False, str(e)[:80])

            # 6 截图导出
            try:
                sh = await call("cad_export_screenshot",
                                {"path": r"C:\Temp\cad_smoke_shot.png"})
                rec("screenshot_export", sh.get("ok") is True,
                    str((sh.get("data") or {}).get("saved_path")))
            except Exception as e:                               # noqa: BLE001
                rec("screenshot_export", False, str(e)[:80])

    return results


def main() -> int:
    t0 = time.monotonic()
    try:
        results = asyncio.run(_run_checks())
    except Exception as e:                                   # noqa: BLE001
        results = [("suite_bootstrapped", False,
                    f"{type(e).__name__}: {str(e)[:100]}")]

    dur = time.monotonic() - t0
    all_ok = bool(results) and all(o for _, o, _ in results)
    if "--json" in sys.argv:
        print(json.dumps({"pass": all_ok, "duration_s": round(dur, 2),
                          "checks": [{"name": n, "ok": o, "detail": d}
                                     for n, o, d in results]}, ensure_ascii=False))
    else:
        print("\n=== cad-mcp smoke suite ===")
        for n, o, d in results:
            print(f" [{'PASS' if o else 'FAIL'}] {n:<24} {d}")
        print(f"=== {'ALL PASS' if all_ok else 'HAS FAILURES'} · {dur:.1f}s ===")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
