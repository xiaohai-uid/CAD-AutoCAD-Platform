"""T011: drawing 校验器（离线纯逻辑，先红后绿）"""
import pytest
from cad_mcp.drawing import validate_item, ParamError


def test_line_duplicate_endpoints():
    with pytest.raises(ParamError):
        validate_item({"kind": "line", "x1": 1, "y1": 1, "x2": 1, "y2": 1})


def test_circle_negative_radius():
    with pytest.raises(ParamError):
        validate_item({"kind": "circle", "cx": 0, "cy": 0, "r": -5})


def test_arc_zero_radius():
    with pytest.raises(ParamError):
        validate_item({"kind": "arc", "cx": 0, "cy": 0, "r": 0,
                       "start_angle": 0, "end_angle": 90})


def test_polyline_needs_two_points():
    with pytest.raises(ParamError):
        validate_item({"kind": "polyline", "points": [[0, 0]]})


def test_polyline_closed_needs_three():
    with pytest.raises(ParamError):
        validate_item({"kind": "polyline", "closed": True,
                       "points": [[0, 0], [10, 0]]})


def test_polyline_consecutive_duplicate():
    with pytest.raises(ParamError):
        validate_item({"kind": "polyline",
                       "points": [[0, 0], [0, 0], [10, 10]]})


def test_rectangle_nonpositive_size():
    for w, h in [(0, 5), (5, -1)]:
        with pytest.raises(ParamError):
            validate_item({"kind": "rectangle", "x": 0, "y": 0, "w": w, "h": h})


def test_text_empty_and_bad_height():
    with pytest.raises(ParamError):
        validate_item({"kind": "text", "text": "", "x": 0, "y": 0})
    with pytest.raises(ParamError):
        validate_item({"kind": "text", "text": "法兰盘", "x": 0, "y": 0, "height": 0})


def test_layer_name_too_long_or_empty():
    with pytest.raises(ParamError):
        validate_item({"kind": "circle", "cx": 0, "cy": 0, "r": 1, "layer": ""})
    with pytest.raises(ParamError):
        validate_item({"kind": "circle", "cx": 0, "cy": 0, "r": 1, "layer": "L" * 256})


def test_unknown_kind():
    with pytest.raises(ParamError):
        validate_item({"kind": "sphere3d"})


def test_valid_items_pass_silently():
    validate_item({"kind": "line", "x1": 0, "y1": 0, "x2": 100, "y2": 0})
    validate_item({"kind": "circle", "cx": 50, "cy": 25, "r": 10})
    validate_item({"kind": "rectangle", "x": 0, "y": 0, "w": 100, "h": 50})
    validate_item({"kind": "text", "text": "法兰盘", "x": 50, "y": 60})
