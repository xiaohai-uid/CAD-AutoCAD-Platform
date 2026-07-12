"""Vision service — analyze images for CAD geometry using OpenCV."""
from __future__ import annotations

from fastapi import FastAPI

from services.vision.engine import VisionEngine
from shared.models import (
    DetectedCircleModel,
    DetectedLineModel,
    DetectedRectModel,
    VisionRequest,
    VisionResponse,
)

app = FastAPI(title="Vision Service", version="0.1.0")
engine = VisionEngine()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "vision"}


@app.post("/vision/analyze", response_model=VisionResponse)
async def analyze_image(req: VisionRequest):
    result = engine.analyze(req.path)
    return VisionResponse(
        lines=[
            DetectedLineModel(
                x1=l.x1, y1=l.y1, x2=l.x2, y2=l.y2,
                length=l.length, angle=l.angle, confidence=l.confidence,
            )
            for l in result.lines
        ],
        circles=[
            DetectedCircleModel(cx=c.cx, cy=c.cy, radius=c.radius, confidence=c.confidence)
            for c in result.circles
        ],
        rects=[
            DetectedRectModel(x=r.x, y=r.y, width=r.width, height=r.height, confidence=r.confidence)
            for r in result.rects
        ],
        image_width=result.image_width,
        image_height=result.image_height,
        success=result.success,
        error=result.error,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
