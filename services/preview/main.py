"""Preview service — generate visual previews via cad_com proxy (no direct COM)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import httpx
from fastapi import FastAPI

from shared.config import get_service_url
from shared.models import PreviewRequest, PreviewResponse

app = FastAPI(title="Preview Service", version="0.1.0")
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=60.0)
    return _client


@app.on_event("shutdown")
async def shutdown():
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


@app.get("/health")
async def health():
    return {"status": "ok", "service": "preview"}


@app.post("/preview/screenshot", response_model=PreviewResponse)
async def screenshot(req: PreviewRequest):
    """Proxy screenshot request to cad_com service (single COM owner)."""
    client = _get_client()
    try:
        com_url = f"{get_service_url('cad_com')}/cad_com/screenshot"
        resp = await client.post(com_url, json=req.model_dump())
        resp.raise_for_status()
        return PreviewResponse(**resp.json())
    except Exception as e:
        return PreviewResponse(success=False, format=req.format, error=str(e))


@app.post("/preview/export_pdf", response_model=PreviewResponse)
async def export_pdf(req: PreviewRequest):
    """Proxy PDF export to cad_com service."""
    client = _get_client()
    try:
        com_url = f"{get_service_url('cad_com')}/cad_com/export_pdf"
        resp = await client.post(com_url, json=req.model_dump())
        resp.raise_for_status()
        return PreviewResponse(**resp.json())
    except Exception as e:
        return PreviewResponse(success=False, format="pdf", error=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8006)
