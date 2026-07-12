"""CAD COM service — execute CAD plans in AutoCAD via COM bridge."""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI
from pydantic import BaseModel

from services.cad_com.engine import CadComEngine
from shared.models import (
    DwgEntityModel,
    DwgScanResponse,
    ExecuteResponse,
    PlanResponse,
    PreviewResponse,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="CAD COM Service", version="0.1.0")
engine = CadComEngine()


class ExecuteRequestBody(BaseModel):
    """Request body for executing a plan via COM."""
    plan: PlanResponse
    job_id: str = ""


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cad_com"}


@app.post("/cad_com/execute", response_model=ExecuteResponse)
async def execute_plan(body: ExecuteRequestBody):
    """Execute a CAD plan against AutoCAD via COM."""
    # Rebuild Plan from PlanResponse using shared converter
    from shared.converters import plan_from_response

    plan = plan_from_response(body.plan)

    result = engine.execute_plan(plan)
    return ExecuteResponse(
        success=result.success,
        entity_count=result.entity_count,
        entities_drawn=result.entities_drawn,
        errors=list(result.errors),
    )


@app.get("/cad_com/status")
async def com_status():
    """Check COM connectivity."""
    return {
        "connected": engine.is_connected,
        "available": True,
    }


@app.post("/cad_com/screenshot", response_model=PreviewResponse)
async def com_screenshot(req: PreviewRequest):
    """Take a screenshot of the current AutoCAD viewport."""
    from services.preview.engine import PreviewEngine
    pe = PreviewEngine()
    result = pe.screenshot(req.job_id, req.width, req.height, req.format)
    return PreviewResponse(
        success=result.success,
        file_path=result.file_path,
        format=result.format,
        error=result.error,
    )


@app.post("/cad_com/export_pdf", response_model=PreviewResponse)
async def com_export_pdf(req: PreviewRequest):
    """Export the current AutoCAD drawing to PDF."""
    from services.preview.engine import PreviewEngine
    pe = PreviewEngine()
    result = pe.export_pdf(req.job_id)
    return PreviewResponse(
        success=result.success,
        file_path=result.file_path,
        format=result.format,
        error=result.error,
    )


@app.post("/cad_com/scan_dwg", response_model=DwgScanResponse)
async def com_scan_dwg(req: DwgScanRequest):
    """Scan a DWG file via COM and return its entities."""
    from services.dwg_scan.engine import DwgScanEngine
    dse = DwgScanEngine()
    content = dse.scan(req.path)
    return DwgScanResponse(
        entities=[
            DwgEntityModel(type=e.type, properties=dict(e.properties), layer=e.layer)
            for e in content.entities
        ],
        layers=list(content.layers),
        entity_count=content.entity_count,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8005)
