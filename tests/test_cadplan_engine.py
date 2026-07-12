"""Tests for CADPlanEngine"""
from services.cadplan.engine import CADPlanEngine


class TestCADPlanEngine:
    def setup_method(self):
        self.engine = CADPlanEngine()

    def test_generate_rectangle_plan(self):
        plan = self.engine.generate_from_text("draw a 200x100 rectangle")
        assert len(plan.entities) >= 1
        entity = plan.entities[0]
        assert entity.type == "rectangle"
        assert entity.params["width"] == 200

    def test_generate_circle_plan(self):
        plan = self.engine.generate_from_text("circle radius 50")
        assert len(plan.entities) >= 1
        entity = plan.entities[0]
        assert entity.type == "circle"
        assert entity.params["radius"] == 50

    def test_professional_dwg_has_layers(self):
        plan = self.engine.generate_from_text(
            "draw a 200x100 rectangle", output_level="professional_dwg"
        )
        assert len(plan.layers) >= 1
