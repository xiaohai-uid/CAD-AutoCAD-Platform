"""真机冒烟入口（宪法 III 验收关卡）。

用法（Windows python 直跑，UNC 或本地路径均可）：
  python smoke.py --selfcheck   # 不依赖 AutoCAD
  python smoke.py               # 附着已运行的 AutoCAD 画一条 (0,0)-(100,0) 直线
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # src/

import json  # noqa: E402

from cad_mcp import result as R  # noqa: E402
from cad_mcp.session import AutoCADSession, SessionError  # noqa: E402


def pt(x: float, y: float):
    import pythoncom
    from win32com.client import VARIANT
    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, 0.0])


def selfcheck() -> int:
    import mcp  # noqa: F401
    import win32com.client  # noqa: F401
    print(json.dumps({"selfcheck": "ok"}))
    return 0


def draw_line() -> int:
    session = AutoCADSession()
    try:
        def _ensure_doc(app):
            try:
                return app.ActiveDocument
            except Exception:
                return app.Documents.Add()  # 冒烟专用：无文档则新建空白图

        def _draw(app):
            doc = _ensure_doc(app)
            return doc.ModelSpace.AddLine(pt(0, 0), pt(100, 0))

        line = session.execute(_draw)
        handle = session.call(lambda: line.Handle)
        session.execute(lambda app: app.ZoomExtents())
        print(json.dumps(R.ok("直线已绘制", handles=[handle]), ensure_ascii=True))
        return 0
    except SessionError as e:
        print(json.dumps(R.fail(e.code, e.message), ensure_ascii=True))
        return 1


def main() -> int:
    if "--selfcheck" in sys.argv:
        return selfcheck()
    return draw_line()


if __name__ == "__main__":
    sys.exit(main())
