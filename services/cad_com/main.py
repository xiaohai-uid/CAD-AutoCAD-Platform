"""CAD COM service — interface with AutoCAD via COM"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI

from shared.models import ExecutePlanRequest, JobResponse, JobStatus

logger = logging.getLogger(__name__)

app = FastAPI(title="CAD COM Service", version="0.1.0")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "cad_com"}

@app.post("/cad_com/execute", response_model=JobResponse)
async def execute_plan(req: ExecutePlanRequest):
    # Check if AutoCAD COM is available
    try:
        import win32com.client
        acad = win32com.client.GetActiveObject("AutoCAD.Application")
        version = acad.Version
        return {
            "job_id": req.job_id,
            "status": JobStatus.executing,
            "next_action": "/preview/generate",
            "assumptions": [{"key": "autocad_version", "value": version}],
            "questions": [],
        }
    except Exception as e:
                return {
            "job_id": req.job_id,
            "status": JobStatus.created,
            "next_action": "/preview/simulate",
            "assumptions": [{"key": "com_error", "value": str(e)}],
            "questions": ["AutoCAD is not running. Start AutoCAD and retry, or use simulation mode?"],
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8005)
