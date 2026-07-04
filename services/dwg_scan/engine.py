"""DWG Scan engine — COM-based parsing of AutoCAD DWG files."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class DwgEntity:
    """A single entity extracted from a DWG file."""
    type: str
    properties: dict = field(default_factory=dict)
    layer: str = ""


@dataclass
class DwgContent:
    """Aggregate content extracted from one DWG file."""
    entities: list[DwgEntity] = field(default_factory=list)
    layers: list[str] = field(default_factory=list)
    entity_count: int = 0

    def __post_init__(self) -> None:
        if self.entity_count == 0 and self.entities:
            self.entity_count = len(self.entities)


# ---------------------------------------------------------------------------
# Scan engine
# ---------------------------------------------------------------------------

class DwgScanEngine:
    """Parse and extract data from existing AutoCAD DWG files via COM."""

    def __init__(self) -> None:
        self.app: Any = None

    # ------------------------------------------------------------------
    # COM helpers
    # ------------------------------------------------------------------

    def _ensure_app(self) -> None:
        """Obtain a reference to the running AutoCAD Application via COM."""
        if self.app is not None:
            return
        import win32com.client
        self.app = win32com.client.GetActiveObject("AutoCAD.Application")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self, path: str) -> DwgContent:
        """Open a DWG file via AutoCAD COM and extract its entities.

        Returns an empty *DwgContent* when the file does not exist or when
        any error occurs (no AutoCAD, COM failure, etc.).
        """
        if not os.path.isfile(path):
            return DwgContent()

        try:
            self._ensure_app()
        except Exception:
            return DwgContent()

        try:
            abs_path = os.path.abspath(path)
            doc = self.app.Documents.Open(abs_path)

            try:
                model_space = doc.ModelSpace
                entities: list[DwgEntity] = []
                layers_set: set[str] = set()

                for com_entity in model_space:
                    try:
                        ent_type = getattr(com_entity, "EntityName", "")
                        ent_layer = getattr(com_entity, "Layer", "")
                        ent_color = getattr(com_entity, "Color", None)

                        props: dict[str, Any] = {}
                        if ent_color is not None:
                            props["color"] = int(ent_color)

                        # Common geometry properties
                        for attr in ("StartPoint", "EndPoint",
                                     "Center", "Radius", "Length",
                                     "Area", "TextString", "Width",
                                     "Height", "Angle", "Normal"):
                            try:
                                val = getattr(com_entity, attr, None)
                                if val is not None:
                                    props[attr] = _com_value(val)
                            except Exception:
                                pass

                        entities.append(DwgEntity(
                            type=str(ent_type),
                            properties=props,
                            layer=str(ent_layer),
                        ))
                        if ent_layer:
                            layers_set.add(str(ent_layer))
                    except Exception:
                        # Skip any entity that fails to read
                        continue

                return DwgContent(
                    entities=entities,
                    layers=sorted(layers_set, key=str.lower),
                    entity_count=len(entities),
                )
            finally:
                try:
                    doc.Close(False)  # do not save changes
                except Exception:
                    pass
        except Exception:
            return DwgContent()

    def find(self, path: str, query: dict[str, Any]) -> list[DwgEntity]:
        """Scan *path* and return entities whose properties match *query*.

        The *query* is a dict of ``property_name → expected_value`` pairs;
        an entity is considered a match when **every** pair matches.
        """
        content = self.scan(path)
        if not content.entities:
            return []

        results: list[DwgEntity] = []
        for ent in content.entities:
            try:
                if all(ent.properties.get(k) == v for k, v in query.items()):
                    results.append(ent)
            except Exception:
                continue
        return results

    def edit(self, path: str, operations: list[dict[str, Any]]) -> bool:
        """Placeholder — future: apply edit operations to a DWG file.

        Returns ``False`` until implemented.
        """
        return False


# ===================================================================
# Helpers
# ===================================================================

def _com_value(val: Any) -> Any:
    """Convert a COM variant into a plain Python value."""
    try:
        # SAFEARRAY → tuple
        if hasattr(val, "__len__") and hasattr(val, "__getitem__"):
            if hasattr(val, "Count"):  # COM collection
                return list(val)
            return tuple(float(v) for v in val)
    except Exception:
        pass
    return val
