"""浸泡测试框架（FR-19）：混合操作循环 + 内存/GDI 采样。

用法：
  python -m cad_mcp.soak_test --iterations 120            # 短程（分钟级）
  python -m cad_mcp.soak_test --iterations 4000           # ≈8h 全量档
指标判定：错误 0；GDI 变化 ≤±10；WorkingSet 增幅 ≤25%（短程参考值）。
"""
from __future__ import annotations
import argparse
import asyncio
import ctypes
import json
import os
import statistics
import sys
import time
from ctypes import wintypes

SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")

PROCESS_MEMORY_COUNTERS = None


class _PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


def _mem_ws(h) -> int:
    pmc = _PMC(); pmc.cb = ctypes.sizeof(_PMC)
    psapi = ctypes.WinDLL("Psapi.dll")
    if not psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
        return -1
    return int(pmc.WorkingSetSize)


def _gdi(h) -> int:
    user32 = ctypes.WinDLL("user32.dll")
    return int(user32.GetGuiResources(h, 0))          # GR_GDIOBJECTS


def _open(pid: int):
    k32 = ctypes.WinDLL("kernel32.dll")
    return k32.OpenProcess(0x0410, False, pid)         # QUERY_INFO|VM_READ


def acad_pid_and_handle() -> tuple[int | None, Any]:
    import win32com.client
    import win32process
    try:
        app = win32com.client.GetActiveObject("AutoCAD.Application")
        hwnd = int(app.HWND)
    except Exception:
        return None, None
    import win32api
    _tid, pid = win32process.GetWindowThreadProcessId(hwnd)
    return pid, _open(pid)


async def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=120)
    ap.add_argument("--interval", type=float, default=0.15)
    args = ap.parse_args(argv)

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    _, acad_h = acad_pid_and_handle()
    self_h = ctypes.WinDLL("kernel32.dll").GetCurrentProcess()

    lat: list[float] = []
    samples: list[dict] = []
    errors = 0
    undone = 0

    async with stdio_client(StdioServerParameters(command=sys.executable, args=[SERVER])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()

            async def op(name, a=None):
                t = time.monotonic()
                res = await s.call_tool(name, a or {})
                dt = time.monotonic() - t
                sc = getattr(res, "structuredContent", None)
                ok = bool(sc and sc.get("ok"))
                return dt, ok, sc

            print(f"soak start: {args.iterations} iters", flush=True)
            for i in range(args.iterations):
                try:
                    dt, ok_, _r = await op("cad_draw_circle",
                                           {"cx": 50000 + i * 3, "cy": 10 + (i % 5), "r": 1.2})
                    lat.append(dt * 1000)
                    if not ok_:
                        errors += 1
                    await op("cad_status")
                    if i % 3 == 2:
                        _, ok_u, r_u = await op("cad_undo")
                        if ok_u and (r_u.get("data") or {}).get("removed_handles"):
                            undone += 1
                    if i % 20 == 19:
                        await op("cad_query_entities", {"page": 1, "page_size": 50})
                    if i % 40 == 39:
                        await op("cad_export_screenshot",
                                 {"path": r"C:\Temp\soak_shot.png"})
                except Exception as e:                        # noqa: BLE001
                    errors += 1
                    print(f"[iter {i}] {type(e).__name__}: {e}", flush=True)

                if acad_h:
                    samples.append({"i": i,
                                    "acad_ws": _mem_ws(acad_h),
                                    "acad_gdi": _gdi(acad_h)})
                samples.append({"i": i, "self_ws": _mem_ws(self_h),
                                "self_gdi": _gdi(self_h)})
                time.sleep(args.interval)

    def stat(key):
        vals = [s_[key] for s_ in samples if key in s_ and s_[key] > 0]
        if not vals:
            return {}
        return {"first": vals[0], "last": vals[-1],
                "delta_pct": round((vals[-1] - vals[0]) / max(vals[0], 1) * 100, 1)}

    def fl(key):
        vals = [s_[key] for s_ in samples
                if key in s_ and isinstance(s_[key], int) and s_[key] > 0]
        return (vals[0], vals[-1]) if vals else None

    def pct(a, b):
        return round((b - a) / max(a, 1) * 100, 1)

    aw = fl("acad_ws"); sw = fl("self_ws")
    ag = fl("acad_gdi"); sg = fl("self_gdi")
    report = {
        "iterations": args.iterations,
        "errors": errors,
        "undo_applied": undone,
        "latency_ms": {"p50": round(statistics.median(lat), 1) if lat else None,
                       "p95": round(sorted(lat)[int(len(lat)*0.95)], 1) if lat else None,
                       "max": round(max(lat), 1) if lat else None},
        "acad_ws": {"first": aw[0], "last": aw[1],
                    "delta_pct": pct(aw[0], aw[1])} if aw else None,
        "self_ws": {"first": sw[0], "last": sw[1],
                    "delta_pct": pct(sw[0], sw[1])} if sw else None,
        "acad_gdi_delta": (ag[1]-ag[0]) if ag else None,
        "self_gdi_delta": (sg[1]-sg[0]) if sg else None,
    }
    print(json.dumps(report, ensure_ascii=False))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
