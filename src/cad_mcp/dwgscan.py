"""DWG 扫描输入（FR-14）：即开即关，不留标签。"""
from __future__ import annotations
import os
from collections import Counter

from .result import fail, ok
from .session import AutoCADSession, SessionError


def scan_dwg(session, path: str, sample: int = 20) -> dict:
    win = path if ":" in str(path) else path   # 调用方(server)已转换
    if not os.path.exists(win):
        return fail("FILE_NOT_FOUND", f"DWG 文件不存在：{win}")

    def job(app):
        opened = app.Documents.Open(str(win))
        try:
            ms = opened.ModelSpace
            total = int(ms.Count)
            by_type: dict[str, int] = {}
            layers: dict[str, bool] = {}
            samp = []
            for i in range(total):
                e = ms.Item(i)
                t = str(e.ObjectName)
                by_type[t] = by_type.get(t, 0) + 1
                layers[str(e.Layer)] = True
                if i < sample:
                    samp.append({"handle": str(e.Handle), "type": t,
                                 "layer": str(e.Layer)})
            return {"file": str(win), "total": total,
                    "by_type": by_type,
                    "layers": sorted(layers),
                    "sample": samp}
        finally:
            opened.Close(False)   # 即开即关，不落标签
    try:
        data = session.execute(job, write_safe=False)
    except SessionError as e:
        return fail(e.code, e.message)
    except Exception as e:
        return fail("COM_FAILURE", f"打开或扫描失败（文件被占用/损坏？）：{e}")
    return ok(f"扫描完成：{data['total']} 实体", data=data)
