"""ValidationEngine — validate CAD plans with 4-category checks."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from services.cadplan.engine import Plan


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ValidationIssue:
    """A single validation finding."""
    category: str       # completeness | consistency | executability | professional
    severity: str       # blocking | warning
    message: str
    field: Optional[str] = None


@dataclass
class ValidationResult:
    """Outcome of a validation pass."""
    valid: bool = True
    blocking_questions: list[str] = field(default_factory=list)
    non_blocking_warnings: list[str] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ValidationEngine:
    """Run structural and geometric checks on a CAD Plan."""

    def validate(
        self,
        plan: Plan,
        output_level: str = "sketch",
        unit: str = "mm",
    ) -> ValidationResult:
        """Run all 4 check categories and return the result."""
        result = ValidationResult()
        self._check_completeness(plan, result)
        self._check_consistency(plan, result)
        self._check_executability(plan, result)
        if output_level == "professional_dwg":
            self._check_professional(plan, result)
        result.valid = not any(
            i.severity == "blocking" for i in result.issues
        )
        return result

    # -- private checks ----------------------------------------------------

    def _add_issue(
        self,
        result: ValidationResult,
        category: str,
        severity: str,
        message: str,
        field: Optional[str] = None,
    ) -> None:
        issue = ValidationIssue(
            category=category,
            severity=severity,
            message=message,
            field=field,
        )
        result.issues.append(issue)
        if severity == "blocking":
            result.blocking_questions.append(message)
        else:
            result.non_blocking_warnings.append(message)

    def _check_completeness(self, plan: Plan, result: ValidationResult) -> None:
        """Verify the plan has entities, layers, and required fields."""
        if plan.get_entity_count() == 0:
            self._add_issue(
                result,
                category="completeness",
                severity="blocking",
                message="Plan contains no entities.",
                field="entities",
            )
        if plan.get_layer_count() == 0:
            self._add_issue(
                result,
                category="completeness",
                severity="blocking",
                message="Plan contains no layers.",
                field="layers",
            )
        for i, entity in enumerate(plan.entities):
            if not entity.type:
                self._add_issue(
                    result,
                    category="completeness",
                    severity="blocking",
                    message=f"Entity #{i} is missing its type field.",
                    field=f"entities[{i}].type",
                )
            if not entity.params:
                self._add_issue(
                    result,
                    category="completeness",
                    severity="blocking",
                    message=f"Entity #{i} ({entity.type}) has no parameters.",
                    field=f"entities[{i}].params",
                )

    def _check_consistency(self, plan: Plan, result: ValidationResult) -> None:
        """Check internal consistency — placeholder for future rules."""
        # No consistency checks yet — reserved for cross-entity validation.
        pass

    def _check_executability(self, plan: Plan, result: ValidationResult) -> None:
        """Ensure geometric values are physically valid."""
        for i, entity in enumerate(plan.entities):
            params = entity.params or {}
            # Rectangles: width > 0, height > 0
            if entity.type == "rectangle":
                w = params.get("width", 0)
                h = params.get("height", 0)
                if w <= 0:
                    self._add_issue(
                        result,
                        category="executability",
                        severity="blocking",
                        message=f"Entity #{i} rectangle has non-positive width ({w}).",
                        field=f"entities[{i}].params.width",
                    )
                if h <= 0:
                    self._add_issue(
                        result,
                        category="executability",
                        severity="blocking",
                        message=f"Entity #{i} rectangle has non-positive height ({h}).",
                        field=f"entities[{i}].params.height",
                    )
            # Circles: radius > 0
            if entity.type in ("circle", "arc"):
                r = params.get("radius", 0)
                if r <= 0:
                    self._add_issue(
                        result,
                        category="executability",
                        severity="blocking",
                        message=f"Entity #{i} {entity.type} has non-positive radius ({r}).",
                        field=f"entities[{i}].params.radius",
                    )

    def _check_professional(self, plan: Plan, result: ValidationResult) -> None:
        """Additional checks required for professional_dwg output."""
        if plan.get_layer_count() == 0:
            self._add_issue(
                result,
                category="professional",
                severity="blocking",
                message="Professional DWG requires at least one layer.",
                field="layers",
            )
        if len(plan.dimensions) == 0:
            self._add_issue(
                result,
                category="professional",
                severity="blocking",
                message="Professional DWG requires at least one dimension.",
                field="dimensions",
            )
