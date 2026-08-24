"""图片→几何（FR-13）：OpenCV 可选依赖，缺失优雅降级。"""
from __future__ import annotations
import os
import time

from .result import fail, ok


def import_geometry(path: str, scale: float = 1.0,
                    origin: list[float] | None = None,
                    min_confidence: float = 0.5) -> dict:
    if not os.path.exists(path):
        return fail("FILE_NOT_FOUND", f"图片不存在：{path}")
    try:
        import cv2  # noqa: F401
        import numpy as np
    except ImportError:
        return fail("MISSING_DEP",
                    "未安装 opencv-python-headless",
                    hint="pip install opencv-python-headless 后重试")

    ox, oy = (origin or [0, 0])
    import sys as _s
    print(f"[ig] start {path}", file=_s.stderr, flush=True)
    t0=time.monotonic()
    img = cv2.imread(str(path))
    print(f"[ig] imread {time.monotonic()-t0:.2f}s", file=_s.stderr, flush=True)
    if img is None:
        return fail("INVALID_PARAM", "图片解码失败（格式不支持或损坏）")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    t=time.monotonic(); edges = cv2.Canny(gray, 50, 150); print(f"[ig] canny {time.monotonic()-t:.2f}s",file=_s.stderr,flush=True)
    items: list[dict] = []
    det = {"lines": 0, "circles": 0, "rects": 0}

    t=time.monotonic(); raw_lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60,
                                minLineLength=30, maxLineGap=8)
    print(f"[ig] houghL {time.monotonic()-t:.2f}s",file=_s.stderr,flush=True)
    lines = [] if raw_lines is None else raw_lines
    for l in lines[:60]:
        x1, y1, x2, y2 = map(int, np.asarray(l).ravel()[:4])
        conf = min(1.0, 0.5 + abs(x2 - x1) * abs(y2 - y1) / 40000)
        if conf < min_confidence:
            continue
        # 图像 y 向下 → CAD y 向上
        items.append({"kind": "line", "layer": "THIN",
                      "params": {"x1": ox + x1 * scale, "y1": oy - y1 * scale,
                                 "x2": ox + x2 * scale, "y2": oy - y2 * scale}})
        det["lines"] += 1

    t=time.monotonic(); circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2,
                               minDist=40, param1=120, param2=45,
                               minRadius=12, maxRadius=400)
    print(f"[ig] houghC {time.monotonic()-t:.2f}s",file=_s.stderr,flush=True)
    if circles is not None:
        for c in circles[0][:40]:
            cx, cy, r = map(float, np.asarray(c).ravel()[:3])
            items.append({"kind": "circle", "layer": "OUTLINE",
                          "params": {"cx": ox + cx * scale, "cy": oy - cy * scale,
                                     "radius": r * scale}})
            det["circles"] += 1

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:20]:
        area = cv2.contourArea(cnt)
        if area < 800:
            continue
        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        if len(approx) == 4:
            x, y, w_, h_ = cv2.boundingRect(approx)
            ar = w_ / max(h_, 1)
            if 0.5 < ar < 2.0 and area / (w_ * h_) > 0.6:
                items.append({"kind": "rectangle", "layer": "OUTLINE",
                              "params": {"x": ox + x * scale, "y": oy - (y + h_) * scale,
                                         "width": w_ * scale, "height": h_ * scale}})
                det["rects"] += 1

    return ok(f"检出 线{det['lines']} 圆{det['circles']} 矩形{det['rects']}",
              data={"items": items, "detections": det})
