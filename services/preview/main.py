"""Preview service — generate visual previews of CAD output"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fastapi import FastAPI
from shared.models import PreviewRequest, JobResponse, JobStatus

app = FastAPI(title="Preview Service", version="0.1.0")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "preview"}

@app.post("/preview/generate", response_model=JobResponse)
async def generate_preview(req: PreviewRequest):
    return {
        "job_id": req.job_id,
        "status": JobStatus.completed,
        "next_action": "/artifacts/list",
        "assumptions": [{"key": "format", "value": req.format}],
        "questions": [],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8006)
