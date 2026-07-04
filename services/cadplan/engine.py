"""CADPlanEngine — generate structured CAD execution plans from natural language."""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PlanLayer:
    name: str
    color: int | str
    lineweight: float = 0.5
    description: str = ""


@dataclass
class PlanEntity:
    type: str  # rectangle | circle | line | arc | polyline
    params: dict
    layer: str = "轮廓线"
    depends_on: list[str] = field(default_factory=list)


@dataclass
class PlanDimension:
    type: str  # aligned | linear | diameter | radius
    point1: list[float]
    point2: list[float]
    text: str = ""


@dataclass
class Plan:
    layers: list[PlanLayer] = field(default_factory=list)
    entities: list[PlanEntity] = field(default_factory=list)
    dimensions: list[PlanDimension] = field(default_factory=list)
    texts: list[dict] = field(default_factory=list)
    assumptions: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    output_level: str = "sketch"
    unit: str = "mm"

    def get_entity_count(self) -> int:
        return len(self.entities)

    def get_layer_count(self) -> int:
        return len(self.layers)


# ---------------------------------------------------------------------------
# Default layer definitions
# ---------------------------------------------------------------------------

DEFAULT_LAYERS: list[PlanLayer] = [
    PlanLayer(name="轮廓线", color=7, lineweight=0.5, description="main outline"),
    PlanLayer(name="中心线", color=1, lineweight=0.25, description="center line"),
    PlanLayer(name="标注", color=3, lineweight=0.25, description="dimension"),
    PlanLayer(name="填充", color=8, lineweight=0.0, description="hatch"),
    PlanLayer(name="文字", color=2, lineweight=0.0, description="text"),
]

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

RECT_PATTERN = re.compile(
    r"(?:draw\s+)?(?:a\s+|an\s+)?(?P<width>\d+(?:\.\d+)?)\s*[xX×]\s*(?P<height>\d+(?:\.\d+)?)\s*(?:rectangle)?",
    re.IGNORECASE,
)
RADIUS_PATTERN = re.compile(
    r"(?:circle|radius)\s*(?:radius\s+)?(?P<radius>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
DIAMETER_PATTERN = re.compile(
    r"(?:diameter|dia)\s*(?:diameter\s+)?(?P<diameter>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class CADPlanEngine:
    """Parse natural-language CAD requests into structured Plans."""

    def generate_from_text(
        self,
        text: str,
        output_level: str = "sketch",
        unit: str = "mm",
    ) -> Plan:
        plan = Plan(
            layers=list(DEFAULT_LAYERS),
            output_level=output_level,
            unit=unit,
        )

        # Try rectangle
        m = RECT_PATTERN.search(text)
        if m:
            width = float(m.group("width"))
            height = float(m.group("height"))
            self._add_rectangle(plan, width, height)
            if output_level == "professional_dwg":
                self._add_rectangle_dimensions(plan, width, height)
            return plan

        # Try radius
        m = RADIUS_PATTERN.search(text)
        if m:
            radius = float(m.group("radius"))
            self._add_circle(plan, radius)
            if output_level == "professional_dwg":
                self._add_circle_dimensions(plan, radius)
            return plan

        # Try diameter
        m = DIAMETER_PATTERN.search(text)
        if m:
            radius = float(m.group("diameter")) / 2.0
            self._add_circle(plan, radius)
            if output_level == "professional_dwg":
                self._add_circle_dimensions(plan, radius)
            return plan

        plan.warnings.append(f"Could not parse request: {text!r}")
        return plan

    # -- helpers -----------------------------------------------------------

    def _add_rectangle(self, plan: Plan, width: float, height: float, x: float = 0.0, y: float = 0.0) -> None:
        entity = PlanEntity(
            type="rectangle",
            params={
                "width": width,
                "height": height,
                "x": x,
                "y": y,
            },
            layer="轮廓线",
        )
        plan.entities.append(entity)

    def _add_rectangle_dimensions(self, plan: Plan, width: float, height: float, x: float = 0.0, y: float = 0.0) -> None:
        plan.dimensions.append(
            PlanDimension(
                type="linear",
                point1=[x, y, 0],
                point2=[x + width, y, 0],
                text=str(width),
            )
        )
        plan.dimensions.append(
            PlanDimension(
                type="linear",
                point1=[x, y, 0],
                point2=[x, y + height, 0],
                text=str(height),
            )
        )

    def _add_circle(self, plan: Plan, radius: float, cx: float = 0.0, cy: float = 0.0) -> None:
        entity = PlanEntity(
            type="circle",
            params={
                "radius": radius,
                "cx": cx,
                "cy": cy,
            },
            layer="轮廓线",
        )
        plan.entities.append(entity)

    def _add_circle_dimensions(self, plan: Plan, radius: float, cx: float = 0.0, cy: float = 0.0) -> None:
        plan.dimensions.append(
            PlanDimension(
                type="radius",
                point1=[cx, cy, 0],
                point2=[cx + radius, cy, 0],
                text=f"R{radius}",
            )
        )
