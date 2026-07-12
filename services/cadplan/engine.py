"""CADPlanEngine — generate structured CAD execution plans from natural language."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

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
# Regex patterns — single-entity matchers
# ---------------------------------------------------------------------------

RECT_PATTERN = re.compile(
    r"(?:(?:draw|create|make|add)\s+)?(?:a\s+|an\s+)?"
    r"(?P<width>\d+(?:\.\d+)?)\s*[xX×]\s*(?P<height>\d+(?:\.\d+)?)"
    r"\s*(?:rectangle|rect)?",
    re.IGNORECASE,
)
CIRCLE_RADIUS_PATTERN = re.compile(
    r"(?:circle|円|圆)\s*(?:with\s+)?(?:radius|r|半径)\s*(?:of\s+)?(?P<radius>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
CIRCLE_DIAMETER_PATTERN = re.compile(
    r"(?:circle|円|圆)\s*(?:with\s+)?(?:diameter|dia|d|直径)\s*(?:of\s+)?(?P<diameter>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
# "Φ30" / "phi30" / "直径30" patterns
PHI_PATTERN = re.compile(
    r"(?:[Φφϕ]|phi|直径)\s*(?P<diameter>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
LINE_PATTERN = re.compile(
    r"(?:line|直线|线)\s+(?:from\s+)?"
    r"\(?\s*(?P<x1>-?\d+(?:\.\d+)?)\s*[,，]\s*(?P<y1>-?\d+(?:\.\d+)?)\s*\)?"
    r"(?:\s+to\s+|\s*[,，]\s*)"
    r"\(?\s*(?P<x2>-?\d+(?:\.\d+)?)\s*[,，]\s*(?P<y2>-?\d+(?:\.\d+)?)\s*\)?",
    re.IGNORECASE,
)
ARC_PATTERN = re.compile(
    r"(?:arc|弧|圆弧)\s+(?:center|圆心|中心)\s*\(?\s*(?P<cx>-?\d+(?:\.\d+)?)\s*[,，]\s*(?P<cy>-?\d+(?:\.\d+)?)\s*\)?"
    r"\s+(?:radius|r|半径)\s*(?:of\s+)?(?P<radius>\d+(?:\.\d+)?)"
    r"(?:\s+(?:from|start|起始)\s*(?P<start_angle>-?\d+(?:\.\d+)?))?"
    r"(?:\s+(?:to|end|结束)\s*(?P<end_angle>-?\d+(?:\.\d+)?))?",
    re.IGNORECASE,
)
POLYLINE_PATTERN = re.compile(
    r"(?:polyline|多段线|pline)\s+(?:points|点|pts)\s*"
    r"\[(?P<points>[\d\s,.\-()]+)\]",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class CADPlanEngine:
    """Parse natural-language CAD requests into structured Plans.

    Supports multiple entities per request. The parser scans the text for
    ALL recognized patterns and adds each found entity to the plan.
    """

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

        found_any = False

        # 1. Rectangles
        for m in RECT_PATTERN.finditer(text):
            width = float(m.group("width"))
            height = float(m.group("height"))
            self._add_rectangle(plan, width, height)

            if "horizontal" in text.lower() or "垂直" in text:
                plan.assumptions.append({"key": "orientation", "value": "vertical"})
            found_any = True

        # 2. Circles by radius
        for m in CIRCLE_RADIUS_PATTERN.finditer(text):
            radius = float(m.group("radius"))
            self._add_circle(plan, radius)
            found_any = True

        # 3. Circles by diameter
        for m in CIRCLE_DIAMETER_PATTERN.finditer(text):
            radius = float(m.group("diameter")) / 2.0
            self._add_circle(plan, radius)
            found_any = True

        # 4. Φ/phi diameter shorthand
        for m in PHI_PATTERN.finditer(text):
            radius = float(m.group("diameter")) / 2.0
            self._add_circle(plan, radius)
            found_any = True

        # 5. Lines
        for m in LINE_PATTERN.finditer(text):
            x1, y1 = float(m.group("x1")), float(m.group("y1"))
            x2, y2 = float(m.group("x2")), float(m.group("y2"))
            plan.entities.append(PlanEntity(
                type="line",
                params={"x1": x1, "y1": y1, "z1": 0, "x2": x2, "y2": y2, "z2": 0},
                layer="轮廓线",
            ))
            found_any = True

        # 6. Arcs
        for m in ARC_PATTERN.finditer(text):
            cx = float(m.group("cx"))
            cy = float(m.group("cy"))
            radius = float(m.group("radius")) if m.group("radius") else 10.0
            start_angle = float(m.group("start_angle")) if m.group("start_angle") is not None else 0.0
            end_angle = float(m.group("end_angle")) if m.group("end_angle") is not None else 90.0
            plan.entities.append(PlanEntity(
                type="arc",
                params={
                    "cx": cx, "cy": cy, "radius": radius,
                    "start_angle": start_angle, "end_angle": end_angle,
                },
                layer="轮廓线",
            ))
            found_any = True

        # 7. Add dimensions for professional_dwg
        if output_level == "professional_dwg" and found_any:
            self._add_dimensions(plan)

        if not found_any:
            plan.warnings.append(f"Could not parse request: {text!r}")

        return plan

    # -- helpers -----------------------------------------------------------

    def _add_rectangle(self, plan: Plan, width: float, height: float,
                       x: float = 0.0, y: float = 0.0) -> None:
        plan.entities.append(PlanEntity(
            type="rectangle",
            params={"width": width, "height": height, "x": x, "y": y},
            layer="轮廓线",
        ))

    def _add_circle(self, plan: Plan, radius: float,
                    cx: float = 0.0, cy: float = 0.0) -> None:
        plan.entities.append(PlanEntity(
            type="circle",
            params={"radius": radius, "cx": cx, "cy": cy},
            layer="轮廓线",
        ))

    def _add_dimensions(self, plan: Plan) -> None:
        """Add dimensions for all entities in the plan."""
        for entity in plan.entities:
            if entity.type == "rectangle":
                w = entity.params.get("width", 0)
                h = entity.params.get("height", 0)
                x = entity.params.get("x", 0)
                y = entity.params.get("y", 0)
                plan.dimensions.append(PlanDimension(
                    type="linear",
                    point1=[x, y, 0], point2=[x + w, y, 0], text=str(w),
                ))
                plan.dimensions.append(PlanDimension(
                    type="linear",
                    point1=[x, y, 0], point2=[x, y + h, 0], text=str(h),
                ))
            elif entity.type == "circle":
                cx = entity.params.get("cx", 0)
                cy = entity.params.get("cy", 0)
                r = entity.params.get("radius", 0)
                plan.dimensions.append(PlanDimension(
                    type="radius",
                    point1=[cx, cy, 0], point2=[cx + r, cy, 0], text=f"R{r}",
                ))
