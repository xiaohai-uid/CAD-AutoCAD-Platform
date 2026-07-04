"""PreviewEngine — generate visual previews (screenshots / PDF) from AutoCAD."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class PreviewResult:
    success: bool
    file_path: str | None = None
    format: str = "png"
    error: str | None = None


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class PreviewEngine:
    """Generate screenshots and PDF exports from an active AutoCAD session."""

    def __init__(self) -> None:
        self.controller = None  # CAD controller reference

    # -- connection ---------------------------------------------------------

    def _ensure_controller(self) -> bool:
        """Try to attach to a running AutoCAD instance via COM."""
        if self.controller is not None:
            return True
        try:
            import win32com.client  # type: ignore[import-untyped]
            self.controller = win32com.client.GetActiveObject("AutoCAD.Application")
            return True
        except Exception:
            logger.debug("Preview error")
            return False

    # -- screenshot ---------------------------------------------------------

    def screenshot(
        self,
        job_id: str,
        width: int = 1920,
        height: int = 1080,
        format: str = "png",
    ) -> PreviewResult:
        """Capture a screenshot of the current CAD viewport.

        Steps:
            1. Ensure COM connection to AutoCAD.
            2. Zoom extents.
            3. Export to ``output/{job_id}/preview.{format}``.

        Returns a ``PreviewResult`` indicating success / failure.
        """
        output_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "output", job_id
        )
        output_dir = os.path.normpath(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, f"preview.{format}")

        if not self._ensure_controller():
            return PreviewResult(
                success=False,
                file_path=file_path,
                format=format,
                error="No AutoCAD connection available",
            )

        try:
            doc = self.controller.ActiveDocument
            doc.SendCommand("_.ZoomExtents\n")
            doc.Export(file_path, format, width, height)
            return PreviewResult(
                success=True,
                file_path=file_path,
                format=format,
            )
        except Exception as exc:
            logger.debug("Preview error")
            return PreviewResult(
                success=False,
                file_path=file_path,
                format=format,
                error=str(exc),
            )

    # -- PDF export ---------------------------------------------------------

    def export_pdf(self, job_id: str) -> PreviewResult:
        """Export the current drawing to PDF via AutoCAD's Plot API.

        The PDF is saved to ``output/{job_id}/output.pdf``.
        """
        output_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "output", job_id
        )
        output_dir = os.path.normpath(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, "output.pdf")

        if not self._ensure_controller():
            return PreviewResult(
                success=False,
                file_path=file_path,
                format="pdf",
                error="No AutoCAD connection available",
            )

        try:
            doc = self.controller.ActiveDocument
            doc.Plot.PlotToFile(file_path)
            return PreviewResult(
                success=True,
                file_path=file_path,
                format="pdf",
            )
        except Exception as exc:
            logger.debug("Preview error")
            return PreviewResult(
                success=False,
                file_path=file_path,
                format="pdf",
                error=str(exc),
            )
