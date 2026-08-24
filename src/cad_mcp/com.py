"""专用常驻 COM 线程：所有 COM 调用串行派发回同一线程执行（套间安全）。

教训来源：Blender 插件外部 Socket 通信必须 queue+派发主线程——
COM 套间同理：GetActiveObject 创建于哪个线程，调用就必须回到哪个线程。
"""
from __future__ import annotations
import queue
import threading


class ComExecutor:
    def __init__(self) -> None:
        self._q: "queue.Queue[tuple]" = queue.Queue()
        self._t = threading.Thread(target=self._loop, name="cad-com", daemon=True)
        self._t.start()

    def _loop(self) -> None:  # pragma: no cover - Windows 真机路径
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ImportError:
            pass  # 纯逻辑环境（无 pywin32）退化为普通线程
        while True:
            fn, box = self._q.get()
            if fn is None:
                break
            try:
                box["val"] = fn()
            except BaseException as e:  # noqa: BLE001
                box["err"] = e
            finally:
                box["ev"].set()

    def run(self, fn, timeout_s: float):
        """同步执行；超时抛 TimeoutError（上层转 BUSY_MODAL）。"""
        box: dict = {"ev": threading.Event()}
        self._q.put((fn, box))
        if not box["ev"].wait(timeout_s):
            raise TimeoutError(f"COM 调用 {timeout_s:.0f}s 无响应")
        if "err" in box:
            raise box["err"]
        return box["val"]
