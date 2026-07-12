"""Shared converters for PlanResponse <-> Plan dataclass conversion."""
from __future__ import annotations

from services.cadplan.engine import Plan, PlanDimension, PlanEntity, PlanLayer
from shared.models import PlanResponse


def plan_from_response(pr: PlanResponse) -> Plan:
    """Rebuild a Plan dataclass from a PlanResponse Pydantic model."""
    plan = Plan(
        output_level=pr.output_level,
        unit=pr.unit,
        assumptions=list(pr.assumptions),
        warnings=list(pr.warnings),
    )
    for l in pr.layers:
        plan.layers.append(PlanLayer(
            name=l.name, color=l.color, lineweight=l.lineweight, description=l.description,
        ))
    for e in pr.entities:
        plan.entities.append(PlanEntity(
            type=e.type, params=dict(e.params), layer=e.layer, depends_on=list(e.depends_on),
        ))
    for d in pr.dimensions:
        plan.dimensions.append(PlanDimension(
            type=d.type, point1=list(d.point1), point2=list(d.point2), text=d.text,
        ))
    plan.texts = list(pr.texts)
    return plan


def plan_to_response(plan: Plan) -> PlanResponse:
    """Serialize a Plan dataclass into a PlanResponse Pydantic model."""
    from shared.models import PlanDimensionModel, PlanEntityModel, PlanLayerModel

    return PlanResponse(
        layers=[PlanLayerModel(
            name=l.name, color=l.color, lineweight=l.lineweight, description=l.description,
        ) for l in plan.layers],
        entities=[PlanEntityModel(
            type=e.type, params=dict(e.params), layer=e.layer, depends_on=list(e.depends_on),
        ) for e in plan.entities],
        dimensions=[PlanDimensionModel(
            type=d.type, point1=list(d.point1), point2=list(d.point2), text=d.text,
        ) for d in plan.dimensions],
        texts=list(plan.texts),
        assumptions=list(plan.assumptions),
        warnings=list(plan.warnings),
        output_level=plan.output_level,
        unit=plan.unit,
    )
