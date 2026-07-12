"""Gateway service — CAD Direct Control HTTP orchestrator."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI, HTTPException

from services.gateway.engine import OrchestratorEngine
from shared.models import (
    ArtifactList,
    ConfirmRequest,
    CreateJobRequest,
    JobResponse,
    JobStatus,
)

app = FastAPI(title="CAD Direct Control - Gateway", version="0.1.0")

engine = OrchestratorEngine()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gateway"}


@app.get("/health/services")
async def health_services():
    """Check all downstream services."""
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
    resp = engine.confirm_job(job_id, req.confirmations)
    if resp is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return resp


@app.get("/job/{job_id}/artifacts", response_model=ArtifactList)
async def get_artifacts(job_id: str):
    return ArtifactList(job_id=job_id, status=JobStatus.completed, artifacts={})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
