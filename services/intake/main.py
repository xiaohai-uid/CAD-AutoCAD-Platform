"""Intake service — parse and structure user requests"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI

from services.intake.engine import IntakeEngine
from shared.models import IntakeRequest, IntakeResponse

app = FastAPI(title="Intake Service", version="0.1.0")
engine = IntakeEngine()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "intake"}


@app.post("/intake/parse", response_model=IntakeResponse)
async def parse_request(req: IntakeRequest):
    ctx = engine.parse(req.user_request, req.files)
    return IntakeResponse(
        intent=ctx.intent,
        input_type=ctx.input_type.value if hasattr(ctx.input_type, 'value') else str(ctx.input_type),
        dimensions=ctx.dimensions,
        unit=ctx.unit,
        description=ctx.description,
        files_valid=ctx.files_valid,
        needs_more_info=ctx.needs_more_info,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
