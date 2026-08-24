"""单槽操作日志——Q1 单步撤销的载体：只记最近一次成功工具调用的句柄集。"""
from __future__ import annotations


class OperationJournal:
    def __init__(self) -> None:
        self._slot: tuple[str, list[str]] | None = None

    def record(self, tool: str, handles: list[str]) -> None:
        """记录（覆盖）最近一次操作的 {工具名, 句柄列表}。"""
        self._slot = (tool, list(handles))

    def peek(self) -> tuple[str, list[str]] | None:
        return self._slot

    def take(self) -> tuple[str, list[str]] | None:
        """取出并清空（供 cad_undo 使用）；空则 None。"""
        slot, self._slot = self._slot, None
        return slot
