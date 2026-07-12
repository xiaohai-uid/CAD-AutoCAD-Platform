"""Gateway service - CAD Direct Control HTTP orchestrator."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from services.gateway.engine import OrchestratorEngine
from shared.config import get_service_url
from shared.models import (
    ArtifactList,
    ConfirmRequest,
    CreateJobRequest,
    JobResponse,
    JobStatus,
)

import logging
logger = logging.getLogger("gateway_main")

app = FastAPI(title="CAD Direct Control - Gateway", version="0.1.0")
engine = OrchestratorEngine()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gateway"}


@app.get("/health/services")
async def health_services():
    statuses = await engine.check_all_services()
    all_ok = all(statuses.values())
    return {"status": "ok" if all_ok else "degraded", "services": statuses}


@app.post("/job/create", response_model=JobResponse)
async def create_job(req: CreateJobRequest):
    return await engine.create_job(req)


@app.get("/job/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    resp = engine.get_job(job_id)
    if resp is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return resp


@app.post("/job/{job_id}/confirm", response_model=JobResponse)
async def confirm_job(job_id: str, req: ConfirmRequest):
    resp = await engine.confirm_job(job_id, req.confirmations)
    if resp is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return resp


@app.post("/job/{job_id}/execute", response_model=JobResponse)
async def execute_job(job_id: str):
    resp = await engine.execute_job(job_id)
    if resp is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return resp


@app.get("/job/{job_id}/artifacts", response_model=ArtifactList)
async def get_artifacts(job_id: str):
    """Get job artifacts from the Artifacts service."""
    try:
        art_url = f"{get_service_url('artifacts')}/artifacts/{job_id}"
        resp = await engine.client.get(art_url, timeout=5.0)
        if resp.status_code == 200:
            return ArtifactList(**resp.json())
    except Exception as e:
        logger.warning("Artifact service call failed: %s", e)
    return ArtifactList(job_id=job_id, status=JobStatus.completed, artifacts={})


@app.get("/routes")
async def get_routes():
    return {
        "routes": [
            {"path": "/job/create", "method": "POST", "description": "Create a new CAD job"},
            {"path": "/job/{job_id}", "method": "GET", "description": "Get job status"},
            {"path": "/job/{job_id}/confirm", "method": "POST", "description": "Confirm job with user input"},
            {"path": "/job/{job_id}/execute", "method": "POST", "description": "Execute a validated job"},
            {"path": "/job/{job_id}/artifacts", "method": "GET", "description": "Get job artifacts"},
            {"path": "/health", "method": "GET", "description": "Health check"},
            {"path": "/health/services", "method": "GET", "description": "Check all downstream services"},
            {"path": "/routes", "method": "GET", "description": "List all routes"},
        ],
        "downstream_services": {
            "intake": "http://127.0.0.1:8001",
            "vision": "http://127.0.0.1:8002",
            "cadplan": "http://127.0.0.1:8003",
            "validation": "http://127.0.0.1:8004",
            "cad_com": "http://127.0.0.1:8005",
            "preview": "http://127.0.0.1:8006",
            "dwg_scan": "http://127.0.0.1:8007",
            "artifacts": "http://127.0.0.1:8008",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
