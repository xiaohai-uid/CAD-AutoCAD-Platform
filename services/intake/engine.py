"""IntakeEngine — parse natural language / file-based CAD requests."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from shared.models import InputType

RECT_PATTERN = re.compile(r"(\d+)x(\d+)")
DIAMETER_PATTERN = re.compile(r"\u03a6\s*(\d+(?:\.\d+)?)")
RADIUS_PATTERN = re.compile(r"(?:[Rr]\s*(\d+(?:\.\d+)?)|radius\s+(\d+(?:\.\d+)?))")
ANGLE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\u00b0")
UNIT_PATTERN = re.compile(r"\b(mm|cm|m|inch(?:es)?)\b")

CREATE_WORDS = {"draw", "create", "make", "add", "new", "build", "plot"}
EDIT_WORDS = {"edit", "modify", "change", "update", "adjust", "revise"}

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
    description: str = ""
    files_valid: bool = True
    needs_more_info: bool = False


class IntakeEngine:
    """Parses user request strings into structured ParsedContext."""

    def parse(self, text: str = "", files: list[str] | None = None) -> ParsedContext:
        ctx = ParsedContext()

        # --- Intent ---
        words = text.lower().split()
        first_word = words[0] if words else ""
        if first_word in CREATE_WORDS or any(w in CREATE_WORDS for w in words):
            ctx.intent = "create"
        elif first_word in EDIT_WORDS or any(w in EDIT_WORDS for w in words):
            ctx.intent = "edit"

        # --- Dimensions ---
        if m := RECT_PATTERN.search(text):
            ctx.dimensions["width"] = int(m.group(1))
            ctx.dimensions["height"] = int(m.group(2))
        if m := DIAMETER_PATTERN.search(text):
            ctx.dimensions["diameter"] = float(m.group(1))
        if m := RADIUS_PATTERN.search(text):
            val = m.group(1) or m.group(2)
            if val:
                ctx.dimensions["radius"] = float(val)
        if m := ANGLE_PATTERN.search(text):
            ctx.dimensions["angle"] = float(m.group(1))

        # --- Unit ---
        if m := UNIT_PATTERN.search(text):
            ctx.unit = m.group(1)

        # --- Needs more info ---
        if len(words) < 3:
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
