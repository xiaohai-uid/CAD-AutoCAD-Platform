"""Tests for ValidationEngine"""

from services.cadplan.engine import CADPlanEngine, Plan, PlanEntity
from services.validation.engine import (
    ValidationEngine,
    ValidationIssue,
    ValidationResult,
)


def test_valid_plan_passes():
    engine = ValidationEngine()
    plan = CADPlanEngine().generate_from_text("draw a 200x100 rectangle", "sketch", "mm")
    result = engine.validate(plan, "sketch", "mm")
    assert result.valid is True


def test_empty_plan_fails():
    engine = ValidationEngine()
    result = engine.validate(Plan(), "sketch", "mm")
    assert result.valid is False


def test_negative_radius_fails():
    engine = ValidationEngine()
    plan = Plan()
    plan.entities.append(PlanEntity(type="circle", params={"cx": 0, "cy": 0, "radius": -10}))
    result = engine.validate(plan, "sketch", "mm")
    assert result.valid is False


def test_professional_dwg_needs_dimensions():
    engine = ValidationEngine()
    plan = CADPlanEngine().generate_from_text("draw a 200x100 rectangle", "sketch", "mm")
    # Even though rectangle is valid for sketch, professional_dwg needs dimensions
    result = engine.validate(plan, "professional_dwg", "mm")
    assert result.valid is False  # sketch-level plan has no dimensions


def test_professional_dwg_with_dimensions_passes():
    engine = ValidationEngine()
    plan = CADPlanEngine().generate_from_text("draw a 200x100 rectangle", "professional_dwg", "mm")
    result = engine.validate(plan, "professional_dwg", "mm")
    assert result.valid is True


def test_validation_result_dataclass():
    result = ValidationResult()
    assert result.valid is True
    assert result.blocking_questions == []
    assert result.non_blocking_warnings == []
    assert result.issues == []


def test_validation_issue_dataclass():
    issue = ValidationIssue(
        category="executability",
        severity="blocking",
        message="Negative radius",
        field="entities[0].params.radius",
    )
    assert issue.category == "executability"
    assert issue.severity == "blocking"
    assert issue.message == "Negative radius"
    assert issue.field == "entities[0].params.radius"


def test_missing_entity_type_fails():
    engine = ValidationEngine()
    plan = Plan()
    plan.entities.append(PlanEntity(type="", params={"x": 0}))
    result = engine.validate(plan, "sketch", "mm")
    assert result.valid is False
    # Should have a completeness issue about missing type
    completeness_issues = [i for i in result.issues if i.category == "completeness"]
    assert any("missing its type" in i.message for i in completeness_issues)


def test_non_positive_rectangle_dimensions_fails():
    engine = ValidationEngine()
    plan = Plan()
    plan.entities.append(PlanEntity(type="rectangle", params={"width": -5, "height": 100}))
    result = engine.validate(plan, "sketch", "mm")
    assert result.valid is False


def test_consistency_check_placeholder():
    """_check_consistency is a placeholder — should not raise or affect validity."""
    engine = ValidationEngine()
    plan = CADPlanEngine().generate_from_text("circle radius 50", "sketch", "mm")
    result = engine.validate(plan, "sketch", "mm")
    # Consistency is a no-op; plan should pass based on other checks
    assert result.valid is True
