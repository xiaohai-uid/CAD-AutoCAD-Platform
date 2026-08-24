"""视觉闭环：缩放控制 + AutoCAD 窗口截屏回传（agent 自反馈，★独有）。"""
from __future__ import annotations
import os
import time

from .drawing import _variant_pt
from .result import fail, ok
from .session import AutoCADSession, SessionError


def zoom(session, mode="extents", x1=None, y1=None, x2=None, y2=None) -> dict:
    if mode == "extents":
        job = lambda app: app.ZoomExtents()
    elif mode == "window":
        if None in (x1, y1, x2, y2):
            return fail("INVALID_PARAM", "window 模式需要 x1,y1,x2,y2")
        job = lambda app: app.ZoomWindow(_variant_pt(x1, y1), _variant_pt(x2, y2))
    else:
        return fail("INVALID_PARAM", "mode 仅支持 extents/window")
    try:
        session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)
    return ok(f"已缩放({mode})")


def export_screenshot(session, path: str) -> dict:
    """置前 AutoCAD 主窗口 → 抓取窗口矩形 → PNG 落盘。"""
    if not str(path).lower().endswith(".png"):
        return fail("INVALID_PARAM", "path 必须以 .png 结尾")

    def job(app):
        return int(app.HWND)
    try:
        hwnd = session.execute(job)
    except SessionError as e:
        return fail(e.code, e.message)

    try:
        import win32gui
        win32gui.ShowWindow(hwnd, 3)          # SW_MAXIMIZE
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        time.sleep(0.9)
        l, t, r, b = win32gui.GetWindowRect(hwnd)
        if r - l < 50 or b - t < 50:
            return fail("BUSY_MODAL", "AutoCAD 窗口尺寸异常，请确认界面已打开")
        from PIL import ImageGrab
        img = ImageGrab.grab(bbox=(l, t, r, b))
        os.makedirs(os.path.dirname(os.path.abspath(str(path))), exist_ok=True)
        img.save(path)
        return ok("截图已保存", data={"saved_path": str(path), "size": list(img.size)})
    except Exception as e:
        return fail("COM_FAILURE", f"截屏失败：{e}")
