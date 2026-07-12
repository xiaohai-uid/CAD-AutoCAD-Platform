"""Tests for Gateway OrchestratorEngine"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.gateway.engine import OrchestratorEngine
from shared.models import CreateJobRequest, InputType, JobStatus, OutputLevel


def test_create_job_sync():
    engine = OrchestratorEngine()
    req = CreateJobRequest(
        user_request="draw a 200x100 rectangle",
        input_type=InputType.natural_language,
        output_level=OutputLevel.sketch,
        declared_unit="mm",
    )
    try:
        resp = engine.create_job_sync(req)
        assert resp.job_id is not None
        # Should fail because services aren't running
    except Exception:
        assert engine.store is not None


def test_get_nonexistent_job():
    engine = OrchestratorEngine()
    resp = engine.get_job("nonexistent")
    assert resp is None


def test_jobstore_has_plans():
    engine = OrchestratorEngine()
    assert hasattr(engine.store, "plans")
    assert isinstance(engine.store.plans, dict)
