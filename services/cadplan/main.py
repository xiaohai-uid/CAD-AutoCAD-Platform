"""CADPlan service — generate CAD execution plans"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI

from shared.models import JobResponse, JobStatus, PlanRequest

app = FastAPI(title="CADPlan Service", version="0.1.0")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "cadplan"}

@app.post("/cadplan/generate", response_model=JobResponse)
async def generate_plan(req: PlanRequest):
    return {
        "job_id": "",
        "status": JobStatus.draft_ready,
        "next_action": "/validation/check",
        "assumptions": [
            {"key": "unit", "value": req.unit},
            {"key": "output_level", "value": req.output_level.value},
        ],
        "questions": [],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003)
