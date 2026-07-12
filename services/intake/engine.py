"""IntakeEngine — parse natural language / file-based CAD requests."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from shared.models import InputType

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# "200x100" rectangle dimension
RECT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)")

# "Φ30" / "phi30" / "直径30"
DIAMETER_PATTERN = re.compile(r"(?:[Φφϕ]|phi|直径)\s*(\d+(?:\.\d+)?)", re.IGNORECASE)

# "R30" / "radius 30" / "半径30"
RADIUS_PATTERN = re.compile(r"(?:[Rr]\s*(\d+(?:\.\d+)?)|radius\s+(\d+(?:\.\d+)?)|半径\s*(\d+(?:\.\d+)?))", re.IGNORECASE)

# Angle: "30°" / "30度" / "30 deg"
ANGLE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:°|度|deg|degrees)", re.IGNORECASE)

# "100mm" / "10cm" / "1m" / "2inches"
UNIT_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s*(mm|cm|m|inch|inches|in|ft|feet)\b", re.IGNORECASE)

# Chinese shape keywords
CN_RECT = re.compile(r"(?:矩形|长方形|正方形|方框)", re.IGNORECASE)
CN_CIRCLE = re.compile(r"(?:圆|圆形|圆圈|圆孔|孔)", re.IGNORECASE)
CN_LINE = re.compile(r"(?:直线|线|线段)", re.IGNORECASE)

# Scale detection: "1:50" / "scale 1:100"
SCALE_PATTERN = re.compile(r"(?:scale|比例)\s*(\d+)\s*[:：]\s*(\d+)", re.IGNORECASE)

# Output level keywords
PROFESSIONAL_KEYWORDS = {"professional", "详细", "标准", "正式", "dwg", "打印", "完整"}
SKETCH_KEYWORDS = {"sketch", "草图", "草稿", "quick", "粗略", "draft"}

# Intent keywords
CREATE_WORDS = {"draw", "create", "make", "add", "new", "build", "plot",
                "画", "绘制", "创建", "新建", "添加", "生成"}
EDIT_WORDS = {"edit", "modify", "change", "update", "adjust", "revise",
              "修改", "编辑", "调整", "更改", "更新"}

EXT_MAP: dict[str, InputType] = {
    ".png": InputType.image,
    ".jpg": InputType.image,
    ".jpeg": InputType.image,
    ".pdf": InputType.pdf,
    ".dwg": InputType.dwg,
}


@dataclass
class ParsedContext:
    intent: str = ""
    input_type: InputType = InputType.natural_language
    dimensions: dict = field(default_factory=dict)
    unit: str = "mm"
    scale: float | None = None
    description: str = ""
    files_valid: bool = True
    needs_more_info: bool = False
    entity_count_estimate: int = 0


class IntakeEngine:
    """Parses user request strings into structured ParsedContext.

    Supports Chinese and English CAD commands with dimension extraction,
    unit detection, scale inference, and output level hints.
    """

    def parse(self, text: str = "", files: list[str] | None = None) -> ParsedContext:
        ctx = ParsedContext()
        words = text.lower().split()

        # --- Intent ---
        first_word = words[0] if words else ""
        if first_word in CREATE_WORDS or any(w in CREATE_WORDS for w in words):
            ctx.intent = "create"
        elif first_word in EDIT_WORDS or any(w in EDIT_WORDS for w in words):
            ctx.intent = "edit"

        # --- Dimensions ---
        # Rectangles: "200x100" or "200 × 100"
        if m := RECT_PATTERN.search(text):
            ctx.dimensions["width"] = float(m.group(1))
            ctx.dimensions["height"] = float(m.group(2))

        # Diameter: "Φ30" / "phi 30"
        if m := DIAMETER_PATTERN.search(text):
            ctx.dimensions["diameter"] = float(m.group(1))

        # Radius: "R30" / "radius 30" / "半径30"
        if m := RADIUS_PATTERN.search(text):
            val = m.group(1) or m.group(2) or m.group(3)
            if val:
                ctx.dimensions["radius"] = float(val)

        # Angle: "30°" / "30度"
        if m := ANGLE_PATTERN.search(text):
            ctx.dimensions["angle"] = float(m.group(1))

        # --- Unit detection ---
        # Check for explicit unit patterns like "100mm" or "10 cm"
        unit_map = {
            "mm": "mm", "cm": "cm", "m": "m",
            "inch": "inch", "inches": "inch", "in": "inch",
            "ft": "ft", "feet": "ft",
        }
        if m := UNIT_PATTERN.search(text):
            unit_str = m.group(2).lower()
            ctx.unit = unit_map.get(unit_str, unit_str)
        else:
            # Check for standalone unit keywords
            unit_words = re.findall(r"\b(mm|cm|m|inch|inches|in|ft|feet|毫米|厘米|米|英寸)\b", text.lower())
            if unit_words:
                u = unit_words[-1]
                ctx.unit = {"毫米": "mm", "厘米": "cm", "米": "m", "英寸": "inch"}.get(u, u)

        # --- Scale ---
        if m := SCALE_PATTERN.search(text):
            num, den = int(m.group(1)), int(m.group(2))
            if den > 0:
                ctx.scale = num / den

        # --- Entity count estimate ---
        shape_count = 0
        if RECT_PATTERN.search(text):
            shape_count += 1
        if CN_RECT.search(text):
            shape_count += 1
        if DIAMETER_PATTERN.search(text) or RADIUS_PATTERN.search(text):
            shape_count += 1
        if CN_CIRCLE.search(text):
            shape_count += 1
        if CN_LINE.search(text):
            shape_count += 1
        ctx.entity_count_estimate = max(1, shape_count)

        # --- Needs more info (only for very short vague requests) ---
        if len(words) < 2 and not files:
            ctx.needs_more_info = True
        elif len(words) < 3 and not any(p.search(text) for p in [RECT_PATTERN, DIAMETER_PATTERN, RADIUS_PATTERN, CN_CIRCLE, CN_RECT]):
            ctx.needs_more_info = True

        # --- Files ---
        files = files or []
        if files:
            valid_count = 0
            ext_lower = ""
            for f in files:
                if os.path.isfile(f):
                    valid_count += 1
                    ext_lower = os.path.splitext(f)[1].lower()
            ctx.files_valid = valid_count == len(files)
            matched = EXT_MAP.get(ext_lower)
            if matched:
                ctx.input_type = matched
            else:
                ctx.input_type = InputType.image  # fallback

        # --- Description ---
        ctx.description = text

        return ctx
