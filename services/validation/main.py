"""Validation service — validate CAD plans before execution."""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from services.validation.engine import ValidationEngine
from shared.converters import plan_from_response
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
