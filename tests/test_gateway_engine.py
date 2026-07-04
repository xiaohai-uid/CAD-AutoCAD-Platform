"""Tests for Gateway OrchestratorEngine"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.gateway.engine import OrchestratorEngine
from shared.models import CreateJobRequest, InputType, OutputLevel


def test_create_job():
    engine = OrchestratorEngine()
    req = CreateJobRequest(
        user_request="draw a 200x100 rectangle",
        input_type=InputType.natural_language,
        output_level=OutputLevel.sketch,
        declared_unit="mm",
    )
    resp = engine.create_job(req)
    assert resp.job_id is not None
    assert resp.status.value == "draft_ready"


def test_get_nonexistent_job():
    engine = OrchestratorEngine()
    resp = engine.get_job("nonexistent")
    assert resp is None
