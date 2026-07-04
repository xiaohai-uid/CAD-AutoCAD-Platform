"""Shared Pydantic models for CAD Direct Control Platform"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    created = "created"
    intake = "intake"
    analyzing = "analyzing"
    planning = "planning"
    draft_ready = "draft_ready"
    needs_confirmation = "needs_confirmation"
    executing = "executing"
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
    declared_scale: Optional[float] = None
    context_id: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    next_action: Optional[str] = None
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
    size_bytes: Optional[int] = None


class ArtifactList(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str = ""
    completed_at: Optional[str] = None
    artifacts: dict[str, ArtifactInfo] = {}


class PlanRequest(BaseModel):
    user_request: str
    vision_analysis_id: Optional[str] = None
    dwg_scan_id: Optional[str] = None
    output_level: OutputLevel = OutputLevel.sketch
    unit: str = "mm"
    declared_scale: Optional[float] = None


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
