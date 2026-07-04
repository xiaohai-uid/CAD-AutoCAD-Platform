import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.intake.engine import IntakeEngine


def test_parse_rectangle_dimensions():
    engine = IntakeEngine()
    ctx = engine.parse("draw a 200x100 rectangle")
    assert ctx.dimensions["width"] == 200
    assert ctx.dimensions["height"] == 100
    assert ctx.intent == "create"


def test_parse_circle():
    engine = IntakeEngine()
    ctx = engine.parse("create a circle with radius 50")
    assert ctx.dimensions["radius"] == 50


def test_parse_with_diameter():
    engine = IntakeEngine()
    ctx = engine.parse("\u03a630 hole")
    assert ctx.dimensions["diameter"] == 30


def test_parse_needs_more_info():
    engine = IntakeEngine()
    ctx = engine.parse("hi")
    assert ctx.needs_more_info is True


def test_parse_edit_intent():
    engine = IntakeEngine()
    ctx = engine.parse("modify the rectangle width to 150")
    assert ctx.intent == "edit"


def test_parse_invalid_file():
    engine = IntakeEngine()
    ctx = engine.parse("draw this", files=["nonexistent.png"])
    assert ctx.files_valid is False
