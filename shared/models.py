"""Shared Pydantic models for CAD Direct Control Platform"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class JobStatus(str, Enum):
    created = "created"
    intake_pending = "intake_pending"
    vision_pending = "vision_pending"
    plan_pending = "plan_pending"
    validation_pending = "validation_pending"
    draft_ready = "draft_ready"
    needs_confirmation = "needs_confirmation"
    executing = "executing"
    saving = "saving"
    preview_pending = "preview_pending"
    archiving = "archiving"
    completed = "completed"
    error = "error"


class InputType(str, Enum):
    natural_language = "natural_language"
    image = "image"
    pdf = "pdf"
    dwg = "dwg"
    mixed = "mixed"


class OutputLevel(str, Enum):
    sketch = "sketch"
    professional_dwg = "professional_dwg"


class CreateJobRequest(BaseModel):
    intent: str = "create_or_edit_cad"
    input_type: InputType = InputType.natural_language
    user_request: str
    files: list[str] = []
    output_level: OutputLevel = OutputLevel.sketch
    declared_unit: str = "mm"
    declared_scale: float | None = None
    context_id: str | None = None


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    next_action: str | None = None
    assumptions: list[dict] = []
    questions: list[str] = []
    created_at: str = ""


class ConfirmRequest(BaseModel):
    confirmations: dict[str, str | bool]


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}


class ArtifactInfo(BaseModel):
    path: str
    size_bytes: int | None = None


class ArtifactList(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str = ""
    completed_at: str | None = None
    artifacts: dict[str, ArtifactInfo] = {}


class PlanRequest(BaseModel):
    user_request: str
    vision_analysis_id: str | None = None
    dwg_scan_id: str | None = None
    output_level: OutputLevel = OutputLevel.sketch
    unit: str = "mm"
    declared_scale: float | None = None


class IntakeRequest(BaseModel):
    user_request: str
    files: list[str] = []
    output_level: OutputLevel = OutputLevel.sketch


class VisionRequest(BaseModel):
    path: str


class ValidationRequest(BaseModel):
    plan_id: str
    output_level: OutputLevel = OutputLevel.sketch
    unit: str = "mm"


class ExecutePlanRequest(BaseModel):
    plan: dict
    job_id: str


class PreviewRequest(BaseModel):
    job_id: str
    width: int = 1920
    height: int = 1080
    format: str = "png"


# ---------------------------------------------------------------------------
# Service-to-service response models (for HTTP microservice communication)
# ---------------------------------------------------------------------------


class IntakeResponse(BaseModel):
    """Structured response from the Intake service."""
    intent: str = ""
    input_type: str = "natural_language"
    dimensions: dict = {}
    unit: str = "mm"
    description: str = ""
    files_valid: bool = True
    needs_more_info: bool = False


class PlanEntityModel(BaseModel):
    """Serializable entity in a CAD plan."""
    type: str
    params: dict = {}
    layer: str = "轮廓线"
    depends_on: list[str] = []


class PlanLayerModel(BaseModel):
    """Serializable layer in a CAD plan."""
    name: str
    color: int | str = 7
    lineweight: float = 0.5
    description: str = ""


class PlanDimensionModel(BaseModel):
    """Serializable dimension in a CAD plan."""
    type: str
    point1: list[float]
    point2: list[float]
    text: str = ""


class PlanResponse(BaseModel):
    """Serialized CAD plan from the CADPlan service."""
    layers: list[PlanLayerModel] = []
    entities: list[PlanEntityModel] = []
    dimensions: list[PlanDimensionModel] = []
    texts: list[dict] = []
    assumptions: list[dict] = []
    warnings: list[str] = []
    output_level: str = "sketch"
    unit: str = "mm"


class ValidationIssueModel(BaseModel):
    """A single validation finding."""
    category: str = ""
    severity: str = "warning"
    message: str = ""
    field: str | None = None


class ValidationResponse(BaseModel):
    """Response from the Validation service."""
    valid: bool = True
    blocking_questions: list[str] = []
    non_blocking_warnings: list[str] = []
    issues: list[ValidationIssueModel] = []


class DetectedLineModel(BaseModel):
    """A line detected in an image."""
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    length: float = 0.0
    angle: float = 0.0
    confidence: float = 0.0


class DetectedCircleModel(BaseModel):
    """A circle detected in an image."""
    cx: float = 0.0
    cy: float = 0.0
    radius: float = 0.0
    confidence: float = 0.0


class DetectedRectModel(BaseModel):
    """A rectangle detected in an image."""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    confidence: float = 0.0


class VisionResponse(BaseModel):
    """Response from the Vision service."""
    lines: list[DetectedLineModel] = []
    circles: list[DetectedCircleModel] = []
    rects: list[DetectedRectModel] = []
    image_width: int = 0
    image_height: int = 0
    success: bool = False
    error: str | None = None


class DwgEntityModel(BaseModel):
    """An entity from a DWG file."""
    type: str = ""
    properties: dict = {}
    layer: str = ""


class DwgScanResponse(BaseModel):
    """Response from the DWG Scan service."""
    entities: list[DwgEntityModel] = []
    layers: list[str] = []
    entity_count: int = 0


class ExecuteResponse(BaseModel):
    """Response from the CAD COM execution service."""
    success: bool = False
    entity_count: int = 0
    entities_drawn: int = 0
    errors: list[str] = []


class PreviewResponse(BaseModel):
    """Response from the Preview service."""
    success: bool = False
    file_path: str | None = None
    format: str = "png"
    error: str | None = None
