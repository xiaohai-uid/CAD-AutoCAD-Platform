"""Tests for CadComEngine"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.cad_com.engine import CadComEngine
from services.cadplan.engine import Plan

def test_execute_empty_plan():
    engine = CadComEngine()
    result = engine.execute_plan(Plan())
    assert result.success is False
    assert "No entities" in " ".join(result.errors)
