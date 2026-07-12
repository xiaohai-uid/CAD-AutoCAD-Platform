"""Tests for enhanced Intake NLP engine"""
from services.intake.engine import IntakeEngine


class TestIntakeNLPEnhanced:
    def setup_method(self):
        self.engine = IntakeEngine()

    def test_chinese_rectangle(self):
        """Chinese CAD command."""
        ctx = self.engine.parse("draw a 200x100 rectangle")
        assert ctx.dimensions["width"] == 200
        assert ctx.dimensions["height"] == 100
        assert ctx.intent == "create"

    def test_chinese_circle_phi(self):
        """Diameter symbol detection."""
        ctx = self.engine.parse("draw a circle Phi30")
        assert ctx.dimensions["diameter"] == 30

    def test_chinese_radius(self):
        """Radius keyword."""
        ctx = self.engine.parse("draw a circle radius 50")
        assert ctx.dimensions["radius"] == 50

    def test_unit_detection_cm(self):
        """Should detect cm unit."""
        ctx = self.engine.parse("draw a 100x50 rectangle in cm")
        assert ctx.unit == "cm"

    def test_scale_detection(self):
        """Should detect scale 1:50."""
        ctx = self.engine.parse("draw a house scale 1:50")
        assert ctx.scale is not None
        assert abs(ctx.scale - 0.02) < 0.001

    def test_entity_count_estimate(self):
        """Should estimate number of shapes."""
        ctx = self.engine.parse("draw a 200x100 rectangle and a circle radius 50")
        assert ctx.entity_count_estimate >= 1

    def test_short_request_needs_info(self):
        """Very short requests should need more info."""
        ctx = self.engine.parse("hi")
        assert ctx.needs_more_info is True

    def test_detailed_request_no_needs_info(self):
        """Detailed requests should not need more info."""
        ctx = self.engine.parse("draw a 200x100 rectangle")
        assert ctx.needs_more_info is False

    def test_angle_pattern(self):
        """Should detect angle."""
        ctx = self.engine.parse("arc at 30 deg")
        assert ctx.dimensions["angle"] == 30

    def test_knowledge_intent(self):
        """Knowledge question should not be treated as create/edit."""
        ctx = self.engine.parse("what is AutoCAD?")
        assert ctx.intent == ""
