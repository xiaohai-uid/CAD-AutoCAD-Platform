"""Artifacts service — manage output files and artifacts with SQLite storage."""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from services.artifacts.engine import ArtifactManager
from shared.models import ArtifactInfo, ArtifactList, JobStatus

app = FastAPI(title="Artifacts Service", version="0.1.0")
manager = ArtifactManager()


class StoreArtifactRequest(BaseModel):
    job_id: str
    files: dict[str, str] = {}
    metadata: dict = {}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "artifacts"}


@app.post("/artifacts/store")
async def store_artifact(req: StoreArtifactRequest):
    record = manager.store(req.job_id, req.files, req.metadata)
    return {"job_id": record.job_id, "created_at": record.created_at, "files": record.files}


@app.get("/artifacts/{job_id}", response_model=ArtifactList)
async def list_artifacts(job_id: str):
    record = manager.get(job_id)
    if record is None:
        return ArtifactList(job_id=job_id, status=JobStatus.completed, artifacts={})
    artifacts = {
        name: ArtifactInfo(path=path)
        for name, path in record.files.items()
    }
    return ArtifactList(
        job_id=record.job_id,
        status=JobStatus.completed,
        created_at=record.created_at,
        artifacts=artifacts,
    )


@app.delete("/artifacts/{job_id}")
async def delete_artifact(job_id: str):
    deleted = manager.delete(job_id)
    return {"deleted": deleted}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8008)
