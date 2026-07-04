"""Vision engine — OpenCV-based image analysis for CAD geometry detection."""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Detected primitives
# ---------------------------------------------------------------------------

@dataclass
class DetectedLine:
    """A single line segment detected in the image."""
    x1: float
    y1: float
    x2: float
    y2: float
    length: float
    angle: float          # degrees from horizontal
    confidence: float     # 0.0 – 1.0

    def __post_init__(self) -> None:
        # Auto-compute length / angle if zero-valued and coords are known
        if self.length == 0.0 or self.angle == 0.0:
            dx = self.x2 - self.x1
            dy = self.y2 - self.y1
            self.length = math.hypot(dx, dy)
            self.angle = math.degrees(math.atan2(dy, dx))


@dataclass
class DetectedCircle:
    """A single circle detected in the image."""
    cx: float
    cy: float
    radius: float
    confidence: float     # 0.0 – 1.0


@dataclass
class DetectedRect:
    """A single rectangle detected in the image."""
    x: float
    y: float
    width: float
    height: float
    confidence: float     # 0.0 – 1.0


# ---------------------------------------------------------------------------
# Aggregate result
# ---------------------------------------------------------------------------

@dataclass
class VisionResult:
    """Result of an image analysis pass."""
    lines: list[DetectedLine] = field(default_factory=list)
    circles: list[DetectedCircle] = field(default_factory=list)
    rects: list[DetectedRect] = field(default_factory=list)
    image_width: int = 0
    image_height: int = 0
    success: bool = False
    error: str | None = None


# ---------------------------------------------------------------------------
# Vision engine
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"})


class VisionEngine:
    """Analyse an image file and extract CAD primitives (lines, circles, rects)."""

    def analyze(self, image_path: str) -> VisionResult:
        """Run the full OpenCV detection pipeline on *image_path*.

        Gracefully handles missing files, unsupported formats, and missing
        ``cv2`` installation.
        """
        # --- File existence ------------------------------------------------
        if not os.path.isfile(image_path):
            return VisionResult(error=f"File not found: {image_path}")

        # --- Extension check ------------------------------------------------
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return VisionResult(error=f"Unsupported format '{ext}'")

        return self._analyze_cv2(image_path)

    # ------------------------------------------------------------------
    # Internal — OpenCV pipeline
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_cv2(image_path: str) -> VisionResult:
        """Execute the detection pipeline (requires ``cv2``)."""
        try:
            import cv2
        except ImportError:
            return VisionResult(
                error="OpenCV (cv2) is not installed. pip install opencv-python"
            )

        img = cv2.imread(image_path)
        if img is None:
            return VisionResult(error=f"Failed to read image: {image_path}")

        height, width = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 1.0)
        edges = cv2.Canny(blurred, 50, 150)

        result = VisionResult(success=True, image_width=width, image_height=height)

        # --- Line detection via probabilistic Hough transform ---------------
        _detect_lines(result, edges)

        # --- Circle detection via Hough gradient method ---------------------
        _detect_circles(result, blurred, gray, height, width)

        # --- Rectangle detection via contour approximation ------------------
        _detect_rects(result, edges)

        return result


# ===================================================================
# Detection helpers (called by _analyze_cv2)
# ===================================================================


def _detect_lines(result: VisionResult, edges: object) -> None:
    """Populate *result.lines* from Canny edges via HoughLinesP."""
    import cv2

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=math.pi / 180,
        threshold=50,
        minLineLength=30,
        maxLineGap=10,
    )
    if lines is None:
        return

    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        angle = math.degrees(math.atan2(dy, dx))
        # Confidence is a heuristic based on length (longer lines are more trusted)
        confidence = min(1.0, length / 500.0)
        result.lines.append(
            DetectedLine(
                x1=float(x1),
                y1=float(y1),
                x2=float(x2),
                y2=float(y2),
                length=length,
                angle=angle,
                confidence=round(confidence, 4),
            )
        )


def _detect_circles(result: VisionResult, blurred: object, gray: object,
                    height: int, width: int) -> None:
    """Populate *result.circles* via HoughCircles."""
    import cv2
    import numpy as np

    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min(height, width) // 4,
        param1=100,
        param2=30,
        minRadius=5,
        maxRadius=min(height, width) // 2,
    )
    if circles is None:
        return

    circles = np.round(circles[0, :]).astype(int)
    for cx, cy, r in circles:
        confidence = min(1.0, r / 200.0)
        result.circles.append(
            DetectedCircle(
                cx=float(cx),
                cy=float(cy),
                radius=float(r),
                confidence=round(confidence, 4),
            )
        )


def _detect_rects(result: VisionResult, edges: object) -> None:
    """Populate *result.rects* via contour detection + approxPolyDP."""
    import cv2

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        perimeter = cv2.arcLength(cnt, closed=True)
        approx = cv2.approxPolyDP(cnt, epsilon=0.04 * perimeter, closed=True)

        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            area_actual = cv2.contourArea(cnt)
            area_bbox = float(w * h)
            ratio = area_actual / area_bbox if area_bbox > 0 else 0
            # Accept rectangles that fill at least 60 % of their bounding box
            if ratio < 0.6:
                continue
            confidence = min(1.0, ratio)
            result.rects.append(
                DetectedRect(
                    x=float(x),
                    y=float(y),
                    width=float(w),
                    height=float(h),
                    confidence=round(confidence, 4),
                )
            )
