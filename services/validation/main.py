"""Validation service — validate CAD plans before execution"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI
from shared.models import ValidationRequest, JobResponse, JobStatus

app = FastAPI(title="Validation Service", version="0.1.0")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "validation"}

@app.post("/validation/check", response_model=JobResponse)
async def validate_plan(req: ValidationRequest):
    return {
        "job_id": "",
        "status": JobStatus.created,
        "next_action": "/cad_com/execute",
        "assumptions": [
            {"key": "plan_valid", "value": "true"},
            {"key": "unit", "value": req.unit},
        ],
        "questions": [],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8004)
