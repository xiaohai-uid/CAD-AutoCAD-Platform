"""DWG Scan service — proxy DWG file scanning through cad_com service (no direct COM)."""
from __future__ import annotations

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from shared.config import get_service_url
from shared.models import DwgEntityModel, DwgScanResponse

app = FastAPI(title="DWG Scan Service", version="0.1.0")
_client: httpx.AsyncClient | None = None


class DwgScanRequest(BaseModel):
    path: str


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=120.0)
    return _client


@app.on_event("shutdown")
async def shutdown():
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


@app.get("/health")
async def health():
    return {"status": "ok", "service": "dwg_scan"}


@app.post("/dwg_scan/scan", response_model=DwgScanResponse)
async def scan_dwg(req: DwgScanRequest):
    """Proxy DWG scan to cad_com service (single COM owner)."""
    client = _get_client()
    try:
        com_url = f"{get_service_url('cad_com')}/cad_com/scan_dwg"
        resp = await client.post(com_url, json=req.model_dump())
        resp.raise_for_status()
        return DwgScanResponse(**resp.json())
    except Exception as e:
        return DwgScanResponse(entity_count=0)


@app.post("/dwg_scan/find", response_model=list[DwgEntityModel])
async def find_dwg(req: DwgScanRequest, query: str = "{}"):
    """Find entities in a DWG file via cad_com proxy."""
    import json
    client = _get_client()
    try:
        com_url = f"{get_service_url('cad_com')}/cad_com/scan_dwg"
        resp = await client.post(com_url, json=req.model_dump())
        resp.raise_for_status()
        data = DwgScanResponse(**resp.json())
        query_dict = json.loads(query)
        results = []
        for ent in data.entities:
            if all(ent.properties.get(k) == v for k, v in query_dict.items()):
                results.append(ent)
        return results
    except Exception:
        return []


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8007)
