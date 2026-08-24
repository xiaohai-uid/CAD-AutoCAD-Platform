"""T018: 分页纯函数边界"""
import pytest
from cad_mcp.query import paginate, kind_of


def test_first_page():
    a, b = paginate(250, 1, 100); assert (a, b) == (0, 100)

def test_middle_page():
    a, b = paginate(250, 2, 100); assert (a, b) == (100, 200)

def test_last_partial_page():
    a, b = paginate(250, 3, 100); assert (a, b) == (200, 250)

def test_page_beyond_range_empty():
    a, b = paginate(250, 99, 100); assert (a, b) == (250, 250)

def test_exact_fit_no_extra_page():
    a, b = paginate(200, 2, 100); assert (a, b) == (100, 200)
    a, b = paginate(200, 3, 100); assert (a, b) == (200, 200)

def test_kind_mapping():
    assert kind_of("AcDbLine") == "LINE"
    assert kind_of("AcDbCircle") == "CIRCLE"
    assert kind_of("AcDbArc") == "ARC"
    assert kind_of("AcDbPolyline") == "LWPOLYLINE"
    assert kind_of("AcDbText") == "TEXT"
    assert kind_of("AcDbWhatever") == "AcDbWhatever"

def test_page_bounds_enforced_by_caller_contract():
    # page/page_size 的契约校验在工具层：这里只锁 paginate 对任意输入的稳健性
    assert paginate(0, 1, 100) == (0, 0)
