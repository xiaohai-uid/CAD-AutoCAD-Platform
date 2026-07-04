"""Vision service — analyze images for CAD"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI
from shared.models import VisionRequest, JobResponse, JobStatus

app = FastAPI(title="Vision Service", version="0.1.0")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "vision"}

@app.post("/vision/analyze", response_model=JobResponse)
async def analyze_image(req: VisionRequest):
    return {
        "job_id": "",
        "status": JobStatus.analyzing,
        "next_action": "/cadplan/generate",
        "assumptions": [{"key": "image_path", "value": req.path}],
        "questions": [],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
