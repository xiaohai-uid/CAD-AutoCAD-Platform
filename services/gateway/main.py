"""Gateway service — CAD Direct Control orchestrator"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from shared.models import (
    CreateJobRequest, JobResponse, JobStatus,
    ConfirmRequest, ArtifactList,
)

app = FastAPI(title="CAD Direct Control - Gateway", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store
_jobs: dict[str, JobResponse] = {}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gateway"}


@app.get("/routes")
async def routes():
    return {
        "gateway": [
            {"path": "/health", "method": "GET"},
            {"path": "/routes", "method": "GET"},
            {"path": "/job/create", "method": "POST"},
            {"path": "/job/{job_id}", "method": "GET"},
            {"path": "/job/{job_id}/confirm", "method": "POST"},
            {"path": "/job/{job_id}/artifacts", "method": "GET"},
        ],
        "downstream": {
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


@app.post("/job/create", response_model=JobResponse)
async def create_job(req: CreateJobRequest):
    import uuid
    job_id = str(uuid.uuid4())[:8]
    resp = JobResponse(
        job_id=job_id,
        status=JobStatus.created,
        next_action="/job/intake",
        assumptions=[{"key": "unit", "value": req.declared_unit}],
        questions=[],
    )
    _jobs[job_id] = resp
    return resp


@app.get("/job/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]


@app.post("/job/{job_id}/confirm", response_model=JobResponse)
async def confirm_job(job_id: str, req: ConfirmRequest):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = _jobs[job_id]
    job.status = JobStatus.executing
    job.next_action = "/job/execute"
    _jobs[job_id] = job
    return job


@app.get("/job/{job_id}/artifacts", response_model=ArtifactList)
async def get_artifacts(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return ArtifactList(
        job_id=job_id,
        status=_jobs[job_id].status,
        artifacts={},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
