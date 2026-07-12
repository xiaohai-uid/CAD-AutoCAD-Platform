"""Validation service — validate CAD plans before execution."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI
from pydantic import BaseModel

from services.cadplan.engine import Plan, PlanDimension, PlanEntity, PlanLayer
from services.validation.engine import ValidationEngine
from shared.models import (
    PlanResponse,
    ValidationIssueModel,
    ValidationResponse,
)

app = FastAPI(title="Validation Service", version="0.1.0")
engine = ValidationEngine()


class ValidationRequestBody(BaseModel):
    """Combined request: plan + validation parameters."""
    plan: PlanResponse
    output_level: str = "sketch"
    unit: str = "mm"


def _plan_from_response(pr: PlanResponse) -> Plan:
    """Rebuild a Plan dataclass from a PlanResponse Pydantic model."""
    plan = Plan(
        output_level=pr.output_level,
        unit=pr.unit,
        assumptions=list(pr.assumptions),
        warnings=list(pr.warnings),
    )
    for l in pr.layers:
        plan.layers.append(PlanLayer(name=l.name, color=l.color, lineweight=l.lineweight, description=l.description))
    for e in pr.entities:
        plan.entities.append(PlanEntity(type=e.type, params=dict(e.params), layer=e.layer, depends_on=list(e.depends_on)))
    for d in pr.dimensions:
        plan.dimensions.append(PlanDimension(type=d.type, point1=list(d.point1), point2=list(d.point2), text=d.text))
    plan.texts = list(pr.texts)
    return plan


@app.get("/health")
async def health():
    return {"status": "ok", "service": "validation"}


@app.post("/validation/check", response_model=ValidationResponse)
async def validate_plan(body: ValidationRequestBody):
    """Validate a plan with its output_level and unit."""
    rebuilt = _plan_from_response(body.plan)
    result = engine.validate(rebuilt, output_level=body.output_level, unit=body.unit)
    return ValidationResponse(
        valid=result.valid,
        blocking_questions=list(result.blocking_questions),
        non_blocking_warnings=list(result.non_blocking_warnings),
        issues=[
            ValidationIssueModel(
                category=issue.category,
                severity=issue.severity,
                message=issue.message,
                field=issue.field,
            )
            for issue in result.issues
        ],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8004)
