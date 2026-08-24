"""T005: journal.py 单槽操作日志（Q1 单步撤销载体）"""
import pytest
from cad_mcp.journal import OperationJournal


def test_empty_journal_peek_none():
    j = OperationJournal()
    assert j.peek() is None


def test_record_then_peek():
    j = OperationJournal()
    j.record("cad_draw_line", ["1A", "1B"])
    assert j.peek() == ("cad_draw_line", ["1A", "1B"])


def test_record_overwrites_previous():
    j = OperationJournal()
    j.record("cad_draw_line", ["1A"])
    j.record("cad_draw_circle", ["2C"])
    assert j.peek() == ("cad_draw_circle", ["2C"])  # 只留最近一次


def test_take_returns_and_clears():
    j = OperationJournal()
    j.record("cad_draw_text", ["F0"])
    assert j.take() == ("cad_draw_text", ["F0"])
    assert j.peek() is None


def test_take_on_empty_is_none():
    j = OperationJournal()
    assert j.take() is None
