"""连接会话 v2：可疑态/泄漏上限（FR-16）+ 写防重放语义（FR-17）+ 看门狗（D6）。"""
from __future__ import annotations
import logging
import time
from typing import Any, Callable

from .com import ComExecutor
from .result import NOT_RUNNING, NO_DOCUMENT, BUSY_MODAL, COM_FAILURE


class SessionError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class AutoCADSession:
    """零配置（D2）。可靠性三律见 003 规格：
    ① 写操作绝不自动重放 ② 可疑态快速拒绝 ③ 泄漏上限保护。"""

    def __init__(self, progid: str = "AutoCAD.Application",
                 watchdog_s: float = 15.0,
                 app_getter: Callable[[str], Any] | None = None,
                 max_leaked: int = 5,
                 preflight_s: float = 1.0):
        self._progid = progid
        self._watchdog_s = watchdog_s
        self._preflight_s = min(preflight_s, watchdog_s)
        self._max_leaked = int(max_leaked)
        self._get_active = app_getter or self._win32_get_active
        self._app: Any = None
        self._com = ComExecutor()
        self._consecutive_timeouts = 0

    # ---- 低层 ----------------------------------------------------------
    @staticmethod
    def _win32_get_active(progid: str) -> Any:
        import win32com.client
        return win32com.client.GetActiveObject(progid)

    def call(self, fn: Callable[[], Any]) -> Any:
        try:
            return self._com.run(fn, self._watchdog_s)
        except TimeoutError as e:
            self._consecutive_timeouts += 1
            raise SessionError(BUSY_MODAL,
                               f"AutoCAD {self._watchdog_s:.0f}s 无响应"
                               f"(连续第{self._consecutive_timeouts}次)") from e

    def _attach(self) -> Any:
        try:
            self._app = self._com.run(lambda: self._get_active(self._progid),
                                      self._watchdog_s)
            self._consecutive_timeouts = 0
        except SessionError:
            raise
        except Exception as e:
            raise SessionError(NOT_RUNNING,
                               f"未找到运行中的 AutoCAD 实例（{e}）") from e
        return self._app

    def _probe_and_recover(self) -> bool:
        """短超时探活：成功则清零恢复，返回 True。"""
        try:
            self._com.run(lambda: self._get_active(self._progid),
                          min(self._preflight_s, 1.0))
            self._app = None          # 强制下次全量附着
            self._consecutive_timeouts = 0
            return True
        except Exception as e:
            return False

    def execute(self, fn: Callable[[Any], Any],
                write_safe: bool = True) -> Any:
        """统一入口。

        write_safe=True（默认，变更类）：连接异常时**不自动重放**——
          先惰性重连一次再快速失败，消息提示人工核对（FR-17 防重复绘制）。
        write_safe=False（只读类）：保留一次重连重试。
        连续看门狗超时进入可疑态：预检通过才放行；持续超时快速拒绝；
        泄漏计数达上限后仅保留短探活通道（SC-12）。
        """
        # 可疑态入口检查
        if self._consecutive_timeouts >= self._max_leaked:
            if not self._probe_and_recover():
                raise SessionError(BUSY_MODAL,
                                   "连续多次无响应已达上限，已熔断；"
                                   "请处理 AutoCAD（对话框/挂起）或重启后再试")
        elif self._consecutive_timeouts > 0:
            if not self._probe_and_recover():
                raise SessionError(BUSY_MODAL, "AutoCAD 探活失败，请检查其状态")

        app = self._app or self._attach()
        try:
            return self.call(lambda: fn(app))
        except SessionError:
            raise
        except Exception as e:
            # 连接可能已失效：写不重放 / 读重试一次
            if write_safe:
                self._app = None
                import traceback as _tb
                detail = f"{type(e).__name__}: {e}"
                tb = _tb.format_exc(limit=3)
                lg = logging.getLogger("cad-mcp")
                lg.error("write job failed :: %s :: tb=%s", detail, tb[-300:])
                raise SessionError(
                    COM_FAILURE,
                    f"写入操作中途异常（未自动重试）：{detail[-160:]} | {tb[-160:]}") from None
            app2 = self._attach()
            try:
                return self.call(lambda: fn(app2))
            except SessionError:
                raise
            except Exception as e2:
                raise SessionError(COM_FAILURE, str(e2)) from e2

    def active_document(self, write_safe: bool = False) -> Any:
        def _doc(app):
            try:
                return app.ActiveDocument
            except Exception as e:
                raise SessionError(NO_DOCUMENT, "AutoCAD 无活动文档") from e
        return self.execute(_doc, write_safe=write_safe)

    def status(self) -> dict[str, Any]:
        try:
            self._app = self._app or self._attach()
        except SessionError:
            return {"attached": False, "doc_name": None, "entity_count": None}
        try:
            doc = self.active_document(write_safe=False)
            count = self.call(lambda: doc.ModelSpace.Count)
            name = self.call(lambda: doc.Name)
            return {"attached": True, "doc_name": name, "entity_count": int(count)}
        except SessionError as e:
            if e.code == NO_DOCUMENT:
                return {"attached": True, "doc_name": None, "entity_count": None}
            raise
