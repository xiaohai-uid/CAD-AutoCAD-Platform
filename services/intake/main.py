"""Intake service — parse and structure user requests"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI

from shared.models import IntakeRequest, JobResponse, JobStatus

app = FastAPI(title="Intake Service", version="0.1.0")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "intake"}

@app.post("/intake/parse", response_model=JobResponse)
async def parse_request(req: IntakeRequest):
    # Parse input type and extract intent
    input_type = req.input_type
    word_count = len(req.user_request.split())

    # Basic heuristic parsing
    has_draw = any(w in req.user_request.lower() for w in ["draw", "create", "make", "add"])
    has_edit = any(w in req.user_request.lower() for w in ["edit", "modify", "change", "update"])

    intent = "create" if has_draw else "edit" if has_edit else "unknown"

    return {
        "job_id": "",
        "status": JobStatus.intake,
        "next_action": "/vision/analyze",
        "assumptions": [
            {"key": "intent", "value": intent},
            {"key": "input_type", "value": input_type.value},
            {"key": "word_count", "value": str(word_count)},
        ],
        "questions": [] if word_count > 3 else ["Please provide more details about what you want to create."],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
