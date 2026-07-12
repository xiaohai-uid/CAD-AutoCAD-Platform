"""CADPlan service — generate CAD execution plans from natural language."""
from __future__ import annotations

from fastapi import FastAPI

from services.cadplan.engine import CADPlanEngine
from shared.models import (
    PlanDimensionModel,
    PlanEntityModel,
    PlanLayerModel,
    PlanRequest,
    PlanResponse,
)

app = FastAPI(title="CADPlan Service", version="0.1.0")
engine = CADPlanEngine()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cadplan"}


@app.post("/cadplan/generate", response_model=PlanResponse)
async def generate_plan(req: PlanRequest):
    plan = engine.generate_from_text(
        req.user_request,
        output_level=req.output_level.value if hasattr(req.output_level, 'value') else req.output_level,
        unit=req.unit,
    )
    return PlanResponse(
        layers=[
            PlanLayerModel(
                name=layer.name,
                color=layer.color,
                lineweight=layer.lineweight,
                description=layer.description,
            )
            for layer in plan.layers
        ],
        entities=[
            PlanEntityModel(
                type=entity.type,
                params=entity.params,
                layer=entity.layer,
                depends_on=entity.depends_on,
            )
            for entity in plan.entities
        ],
        dimensions=[
            PlanDimensionModel(
                type=dim.type,
                point1=list(dim.point1) if hasattr(dim.point1, '__iter__') else [dim.point1],
                point2=list(dim.point2) if hasattr(dim.point2, '__iter__') else [dim.point2],
                text=dim.text,
            )
            for dim in plan.dimensions
        ],
        texts=[t for t in plan.texts],
        assumptions=plan.assumptions,
        warnings=plan.warnings,
        output_level=plan.output_level,
        unit=plan.unit,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003)
