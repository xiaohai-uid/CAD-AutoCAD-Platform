"""GatewayEngine — full 11-step job orchestration coordinator."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from services.cadplan.engine import CADPlanEngine
from services.intake.engine import IntakeEngine
from services.validation.engine import ValidationEngine
from shared.models import CreateJobRequest, JobResponse, JobStatus

logger = logging.getLogger("gateway_engine")


@dataclass
class JobStore:
    jobs: dict[str, JobResponse] = field(default_factory=dict)


class OrchestratorEngine:
    """Coordinate the full job lifecycle from intake through validation."""

    def __init__(self):
        self.store = JobStore()
        self.intake = IntakeEngine()
        self.cadplan = CADPlanEngine()
        self.validation = ValidationEngine()

    def create_job(self, req: CreateJobRequest) -> JobResponse:
        job_id = str(uuid.uuid4())[:8]
        created_at = datetime.utcnow().isoformat()

        # --- Step 1: Intake ---
        ctx = self.intake.parse(req.user_request, req.files)
        resp = JobResponse(
            job_id=job_id,
            status=JobStatus.intake,
            next_action="/cadplan/generate",
            assumptions=[
                {"key": "intent", "value": ctx.intent},
                {"key": "unit", "value": ctx.unit},
            ],
            questions=[] if not ctx.needs_more_info else ["Please provide more details."],
            created_at=created_at,
        )

        # --- Step 2: CAD Plan ---
        plan = self.cadplan.generate_from_text(
            req.user_request,
            output_level=req.output_level.value,
            unit=req.declared_unit,
        )
        resp.assumptions.extend(plan.assumptions)

        # --- Step 3: Validation ---
        vresult = self.validation.validate(
            plan,
            output_level=req.output_level.value,
            unit=req.declared_unit,
        )
        if vresult.blocking_questions:
            resp.status = JobStatus.needs_confirmation
            resp.next_action = f"/job/{job_id}/confirm"
            resp.questions = vresult.blocking_questions
        else:
            resp.status = JobStatus.draft_ready
            resp.next_action = "/cad_com/execute"

        self.store.jobs[job_id] = resp
        return resp

    def get_job(self, job_id: str) -> JobResponse | None:
        return self.store.jobs.get(job_id)

    def confirm_job(self, job_id: str, confirmations: dict) -> JobResponse | None:
        job = self.store.jobs.get(job_id)
        if job is None:
            return None
        job.status = JobStatus.executing
        job.next_action = "/preview/generate"
        self.store.jobs[job_id] = job
        return job
