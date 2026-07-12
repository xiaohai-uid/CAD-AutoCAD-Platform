"""Tests for CADPlanEngine multi-entity parsing"""
from services.cadplan.engine import CADPlanEngine


class TestMultiEntityParsing:
    def setup_method(self):
        self.engine = CADPlanEngine()

    def test_rectangle_and_circle(self):
        """Parse 'draw a 200x100 rectangle and a circle radius 50'."""
        plan = self.engine.generate_from_text("draw a 200x100 rectangle and a circle radius 50")
        types = [e.type for e in plan.entities]
        assert "rectangle" in types
        assert "circle" in types
        assert plan.get_entity_count() >= 2

    def test_rectangle_with_phi_circle(self):
        """Parse 'draw a 200x100 rectangle with a Φ30 hole'."""
        plan = self.engine.generate_from_text("draw a 200x100 rectangle with a Φ30 hole")
        types = [e.type for e in plan.entities]
        assert "rectangle" in types
        assert "circle" in types
        # Check the circle radius is 15 (Φ30 / 2)
        circle = [e for e in plan.entities if e.type == "circle"][0]
        assert circle.params["radius"] == 15.0

    def test_line_drawing(self):
        """Parse 'line from 0,0 to 100,200'."""
        plan = self.engine.generate_from_text("line from 0,0 to 100,200")
        assert plan.get_entity_count() >= 1
        entity = plan.entities[0]
        assert entity.type == "line"
        assert entity.params["x1"] == 0.0
        assert entity.params["y1"] == 0.0
        assert entity.params["x2"] == 100.0
        assert entity.params["y2"] == 200.0

    def test_arc_drawing(self):
        """Parse 'arc center 50,50 radius 30 from 0 to 90'."""
        plan = self.engine.generate_from_text("arc center 50,50 radius 30 from 0 to 90")
        assert plan.get_entity_count() >= 1
        entity = plan.entities[0]
        assert entity.type == "arc"
        assert entity.params["radius"] == 30.0
        assert entity.params["start_angle"] == 0.0
        assert entity.params["end_angle"] == 90.0

    def test_professional_dwg_adds_dimensions(self):
        """professional_dwg output level should add dimensions."""
        plan = self.engine.generate_from_text(
            "draw a 200x100 rectangle", output_level="professional_dwg"
        )
        assert len(plan.dimensions) > 0

    def test_unparseable_request(self):
        """Should warn on unparseable input."""
        plan = self.engine.generate_from_text("do something weird")
        assert len(plan.warnings) > 0
