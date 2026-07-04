"""CadComEngine — execute structured CAD Plans via the COM bridge."""

from __future__ import annotations
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from cad_mcp_bridge.cad_controller import CADController

# Re-use the Plan data classes from the cadplan service
from services.cadplan.engine import Plan, PlanEntity  # noqa: E402

logger = logging.getLogger("cad_com.engine")


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ExecutionResult:
    """Outcome of a plan execution."""
    success: bool = False
    entity_count: int = 0
    entities_drawn: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class CadComEngine:
    """Execute CAD plans against a live AutoCAD instance via COM."""

    def __init__(self) -> None:
        self._controller: Optional[CADController] = None

    # -- connect / disconnect ------------------------------------------------

    def connect(self) -> bool:
        """Start or attach to a CAD instance."""
        if self._controller is None:
            self._controller = CADController()
        return self._controller.start_cad()

    @property
    def is_connected(self) -> bool:
        return self._controller is not None and self._controller.is_running()

    def disconnect(self) -> None:
        """Release the CAD controller."""
        if self._controller is not None:
            try:
                self._controller.close()
            except Exception:
                logger.exception("Error during disconnect")
            self._controller = None

    # -- execute plan -------------------------------------------------------

    def execute_plan(self, plan: Plan) -> ExecutionResult:
        """Execute every entity in *plan* against the active CAD document.

        Failures for individual entities are logged and collected in
        ``ExecutionResult.errors``; the engine keeps going.
        """
        result = ExecutionResult()
        result.entity_count = plan.get_entity_count()

        if result.entity_count == 0:
            result.errors.append("No entities to draw")
            return result

        # Connect if not already connected
        if not self.is_connected:
            ok = self.connect()
            if not ok:
                result.errors.append("Could not connect to CAD")
                return result

        # Ensure layers exist
        for layer in plan.layers:
            try:
                self._controller.create_layer(layer.name)
            except Exception:
                logger.exception("Failed to create layer %s", layer.name)

        drawn = 0
        for entity in plan.entities:
            try:
                self._draw_one(entity, plan)
                drawn += 1
            except Exception as exc:
                msg = f"Failed to draw {entity.type} entity: {exc}"
                logger.exception(msg)
                result.errors.append(msg)

        # Draw texts
        for text_def in plan.texts:
            try:
                self._draw_text(text_def)
                drawn += 1
            except Exception as exc:
                msg = f"Failed to draw text: {exc}"
                logger.exception(msg)
                result.errors.append(msg)

        # Draw dimensions
        for dim in plan.dimensions:
            try:
                self._draw_dimension(dim)
                drawn += 1
            except Exception as exc:
                msg = f"Failed to draw dimension: {exc}"
                logger.exception(msg)
                result.errors.append(msg)

        result.entities_drawn = drawn

        # Zoom to show everything
        try:
            self._controller.zoom_extents()
        except Exception:
            logger.exception("zoom_extents failed")

        result.success = len(result.errors) == 0
        return result

    # -- single-entity dispatch ---------------------------------------------

    def _draw_one(self, entity: PlanEntity, plan: Plan) -> None:
        p = entity.params
        layer = entity.layer

        if entity.type == "rectangle":
            x = p.get("x", 0.0)
            y = p.get("y", 0.0)
            w = p.get("width", 10.0)
            h = p.get("height", 10.0)
            self._controller.draw_rectangle(
                corner1=(x, y, 0), corner2=(x + w, y + h, 0), layer=layer,
            )

        elif entity.type == "circle":
            cx = p.get("cx", 0.0)
            cy = p.get("cy", 0.0)
            radius = p.get("radius", 5.0)
            self._controller.draw_circle(
                center=(cx, cy, 0), radius=radius, layer=layer,
            )

        elif entity.type == "line":
            sp = (p.get("x1", 0.0), p.get("y1", 0.0), p.get("z1", 0.0))
            ep = (p.get("x2", 0.0), p.get("y2", 0.0), p.get("z2", 0.0))
            # Support shorter form
            sp = p.get("start_point", sp)
            ep = p.get("end_point", ep)
            self._controller.draw_line(start_point=sp, end_point=ep, layer=layer)

        elif entity.type == "arc":
            center = (
                p.get("cx", p.get("center_x", 0.0)),
                p.get("cy", p.get("center_y", 0.0)),
                0,
            )
            r = p.get("radius", 5.0)
            sa = p.get("start_angle", 0.0)
            ea = p.get("end_angle", 90.0)
            # Accept nested "center" key
            if "center" in p:
                center = tuple(p["center"][:2]) + (0,)
            self._controller.draw_arc(
                center=center, radius=r,
                start_angle=sa, end_angle=ea,
                layer=layer,
            )

        elif entity.type == "polyline":
            pts = p.get("points", [])
            closed = p.get("closed", False)
            self._controller.draw_polyline(points=pts, closed=closed, layer=layer)

        else:
            raise ValueError(f"Unknown entity type: {entity.type!r}")

    def _draw_text(self, text_def: dict) -> None:
        pos = text_def.get("position", (0, 0, 0))
        txt = text_def.get("text", "")
        height = text_def.get("height", 2.5)
        rotation = text_def.get("rotation", 0)
        layer = text_def.get("layer", "文字")
        self._controller.draw_text(
            position=pos, text=txt,
            height=height, rotation=rotation,
            layer=layer,
        )

    def _draw_dimension(self, dim) -> None:
        self._controller.add_dimension(
            start_point=dim.point1,
            end_point=dim.point2,
            text_position=None,
            textheight=5,
        )

    # -- convenience helpers ------------------------------------------------

    def save(self, path: str) -> bool:
        """Save the current drawing to *path*."""
        if not self.is_connected:
            return False
        return self._controller.save_drawing(path)

    def zoom_extents(self) -> bool:
        """Zoom to fit all geometry."""
        if not self.is_connected:
            return False
        return self._controller.zoom_extents()
