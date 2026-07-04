"""Artifacts service — manage output files and artifacts"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fastapi import FastAPI

from shared.models import ArtifactList, JobStatus

app = FastAPI(title="Artifacts Service", version="0.1.0")

_artifacts: dict[str, ArtifactList] = {}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "artifacts"}

@app.get("/artifacts/{job_id}", response_model=ArtifactList)
async def list_artifacts(job_id: str):
    if job_id not in _artifacts:
        return ArtifactList(job_id=job_id, status=JobStatus.completed, artifacts={})
    return _artifacts[job_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8008)
