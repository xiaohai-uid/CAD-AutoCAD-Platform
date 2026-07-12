"""Tests for DwgScanEngine"""
from services.dwg_scan.engine import DwgContent, DwgEntity, DwgScanEngine

# ---------------------------------------------------------------------------
# scan()
# ---------------------------------------------------------------------------

def test_scan_file_not_found():
    engine = DwgScanEngine()
    result = engine.scan("nonexistent.dwg")
    assert result.entity_count == 0


def test_scan_non_dwg_file():
    """Should gracefully return empty for non-DWG files (no COM crash)."""
    engine = DwgScanEngine()
    result = engine.scan("not_a_file.xyz")
    assert result.entity_count == 0
    assert isinstance(result, DwgContent)


# ---------------------------------------------------------------------------
# find()
# ---------------------------------------------------------------------------

def test_find_no_scan():
    """find() on a non-existent file should return empty list."""
    engine = DwgScanEngine()
    results = engine.find("nonexistent.dwg", {"color": 1})
    assert results == []


# ---------------------------------------------------------------------------
# edit()
# ---------------------------------------------------------------------------

def test_edit_placeholder():
    """edit() should return False until implemented."""
    engine = DwgScanEngine()
    result = engine.edit("test.dwg", [])
    assert result is False


# ---------------------------------------------------------------------------
# DwgEntity / DwgContent dataclass
# ---------------------------------------------------------------------------

def test_dwg_entity_defaults():
    ent = DwgEntity(type="AcDbLine")
    assert ent.type == "AcDbLine"
    assert ent.properties == {}
    assert ent.layer == ""


def test_dwg_entity_full():
    ent = DwgEntity(
        type="AcDbCircle",
        properties={"Center": (0.0, 0.0, 0.0), "Radius": 50.0, "color": 1},
        layer="0",
    )
    assert ent.type == "AcDbCircle"
    assert ent.properties["Radius"] == 50.0
    assert ent.layer == "0"


def test_dwg_content_empty():
    content = DwgContent()
    assert content.entities == []
    assert content.layers == []
    assert content.entity_count == 0


def test_dwg_content_populated():
    entities = [
        DwgEntity(type="AcDbLine", layer="0"),
        DwgEntity(type="AcDbCircle", layer="Walls"),
    ]
    content = DwgContent(entities=entities, layers=["0", "Walls"])
    assert content.entity_count == 2
    assert "Walls" in content.layers


def test_dwg_content_post_init():
    """entity_count is auto-derived from entities if not explicitly set."""
    entities = [DwgEntity(type="AcDbLine")]
    content = DwgContent(entities=entities)
    assert content.entity_count == 1
