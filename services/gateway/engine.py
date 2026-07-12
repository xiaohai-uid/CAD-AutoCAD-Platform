"""GatewayEngine - HTTP-based microservice orchestration for CAD jobs."""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from shared.config import get_service_url
from shared.models import (
    CreateJobRequest,
    IntakeResponse,
    JobResponse,
    JobStatus,
    PlanResponse,
    ValidationResponse,
)

logger = logging.getLogger("gateway_engine")
SERVICE_TIMEOUT = 30.0


@dataclass
class JobStore:
    jobs: dict[str, JobResponse] = field(default_factory=dict)
    plans: dict[str, PlanResponse] = field(default_factory=dict)


class OrchestratorEngine:
    def __init__(self):
        self.store = JobStore()
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=SERVICE_TIMEOUT)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def check_health(self, service_name: str) -> bool:
        url = f"{get_service_url(service_name)}/health"
        try:
            resp = await self.client.get(url, timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def check_all_services(self) -> dict[str, bool]:
        services = ["intake", "vision", "cadplan", "validation",
                     "cad_com", "preview", "dwg_scan", "artifacts"]
        results = await asyncio.gather(
            *[self.check_health(svc) for svc in services],
            return_exceptions=True,
        )
        return {svc: bool(r) for svc, r in zip(services, results, strict=False)}


    async def create_job(self, req: CreateJobRequest) -> JobResponse:
        job_id = str(uuid.uuid4())[:8]
        created_at = datetime.now(timezone.utc).isoformat()
        job_resp = JobResponse(job_id=job_id, status=JobStatus.created, created_at=created_at)

        # Step 1: Intake
        try:
            intake_resp = await self.client.post(
                f"{get_service_url('intake')}/intake/parse",
                json={"user_request": req.user_request, "files": req.files,
                       "output_level": req.output_level.value if hasattr(req.output_level, 'value') else req.output_level},
            )
            intake_resp.raise_for_status()
            intake_data = IntakeResponse(**intake_resp.json())
        except Exception as e:
            job_resp.status = JobStatus.error
            job_resp.next_action = "/retry"
            job_resp.assumptions = [{"key": "error", "value": f"Intake failed: {e}"}]
            self.store.jobs[job_id] = job_resp
            return job_resp

        job_resp.status = JobStatus.intake_pending
        job_resp.assumptions = [{"key": "intent", "value": intake_data.intent},
                                {"key": "unit", "value": intake_data.unit},
                                {"key": "input_type", "value": intake_data.input_type}]
        if intake_data.needs_more_info:
            job_resp.next_action = "/job/confirm"
            job_resp.questions = ["Please provide more details."]
            self.store.jobs[job_id] = job_resp
            return job_resp

        # Step 1b: Vision (if files provided)
        if req.files and intake_data.input_type in ("image", "pdf"):
            job_resp.status = JobStatus.vision_pending
            try:
                for fpath in req.files:
                    vr = await self.client.post(
                        f"{get_service_url('vision')}/vision/analyze",
                        json={"path": fpath},
                    )
                    if vr.status_code == 200:
                        vd = vr.json()
                        job_resp.assumptions.append({"key": f"vision_{fpath}", "value": f"{len(vd.get('lines', []))} lines"})
            except Exception as e:
                logger.warning("Vision analysis failed (non-blocking): %s", e)

        # Step 2: CAD Plan
        job_resp.status = JobStatus.plan_pending
        try:
            plan_resp = await self.client.post(
                f"{get_service_url('cadplan')}/cadplan/generate",
                json={"user_request": req.user_request,
                       "output_level": req.output_level.value if hasattr(req.output_level, 'value') else req.output_level,
                       "unit": req.declared_unit},
            )
            plan_resp.raise_for_status()
            plan_data = PlanResponse(**plan_resp.json())
        except Exception as e:
            job_resp.status = JobStatus.error
            job_resp.next_action = "/retry"
            job_resp.assumptions.append({"key": "error", "value": f"CADPlan failed: {e}"})
            self.store.jobs[job_id] = job_resp
            return job_resp

        job_resp.assumptions.extend(plan_data.assumptions)
        self.store.plans[job_id] = plan_data

        # Step 3: Validation
        job_resp.status = JobStatus.validation_pending
        try:
            val_resp = await self.client.post(
                f"{get_service_url('validation')}/validation/check",
                json={"plan": plan_data.model_dump(),
                       "output_level": req.output_level.value if hasattr(req.output_level, 'value') else req.output_level,
                       "unit": req.declared_unit},
            )
            val_resp.raise_for_status()
            val_data = ValidationResponse(**val_resp.json())
        except Exception as e:
            job_resp.status = JobStatus.error
            job_resp.next_action = "/retry"
            job_resp.assumptions.append({"key": "error", "value": f"Validation failed: {e}"})
            self.store.jobs[job_id] = job_resp
            return job_resp

        if not val_data.valid:
            job_resp.status = JobStatus.needs_confirmation
            job_resp.next_action = f"/job/{job_id}/confirm"
            job_resp.questions = val_data.blocking_questions
        else:
            job_resp.status = JobStatus.draft_ready
            job_resp.next_action = f"/job/{job_id}/execute"

        self.store.jobs[job_id] = job_resp
        return job_resp


    async def confirm_job(self, job_id: str, confirmations: dict) -> JobResponse | None:
        """Record confirmations, re-validate, then proceed."""
        job = self.store.jobs.get(job_id)
        if job is None:
            return None
        plan = self.store.plans.get(job_id)
        if plan is not None:
            try:
                val_resp = await self.client.post(
                    f"{get_service_url('validation')}/validation/check",
                    json={"plan": plan.model_dump(), "output_level": plan.output_level, "unit": plan.unit},
                )
                val_resp.raise_for_status()
                val_data = ValidationResponse(**val_resp.json())
                if not val_data.valid:
                    job.status = JobStatus.needs_confirmation
                    job.next_action = f"/job/{job_id}/confirm"
                    job.questions = val_data.blocking_questions
                    self.store.jobs[job_id] = job
                    return job
            except Exception as e:
                logger.warning("Re-validation after confirm failed: %s", e)
        job.status = JobStatus.draft_ready
        job.next_action = f"/job/{job_id}/execute"
        job.assumptions.append({"key": "confirmed", "value": str(confirmations)})
        self.store.jobs[job_id] = job
        return job

    async def execute_job(self, job_id: str) -> JobResponse | None:
        """Execute a validated job: CAD COM -> Preview -> Artifacts."""
        job = self.store.jobs.get(job_id)
        if job is None:
            return None
        plan = self.store.plans.get(job_id)
        if plan is None:
            job.status = JobStatus.error
            job.next_action = "/retry"
            job.assumptions.append({"key": "error", "value": "No plan found for this job"})
            self.store.jobs[job_id] = job
            return job

        job.status = JobStatus.executing
        self.store.jobs[job_id] = job

        # Step 4: CAD COM execution
        try:
            com_resp = await self.client.post(
                f"{get_service_url('cad_com')}/cad_com/execute",
                json={"plan": plan.model_dump(), "job_id": job_id},
            )
            com_resp.raise_for_status()
            exec_data = com_resp.json()
        except Exception as e:
            job.status = JobStatus.error
            job.next_action = "/retry"
            job.assumptions.append({"key": "error", "value": f"CAD COM failed: {e}"})
            self.store.jobs[job_id] = job
            return job

        if not exec_data.get("success"):
            job.status = JobStatus.error
            job.next_action = "/retry"
            job.assumptions.append({"key": "errors", "value": "; ".join(exec_data.get("errors", []))})
            self.store.jobs[job_id] = job
            return job

        # Step 5: Save
        job.status = JobStatus.saving
        try:
            await self.client.post(
                f"{get_service_url('cad_com')}/cad_com/save",
                json={"path": f"output/{job_id}/drawing.dwg", "job_id": job_id},
            )
        except Exception as e:
            logger.warning("Save failed (continuing): %s", e)

        # Step 6: Preview
        job.status = JobStatus.preview_pending
        try:
            await self.client.post(
                f"{get_service_url('preview')}/preview/screenshot",
                json={"job_id": job_id},
            )
        except Exception as e:
            logger.warning("Preview failed (continuing): %s", e)

        # Step 7: Artifacts
        job.status = JobStatus.archiving
        try:
            await self.client.post(
                f"{get_service_url('artifacts')}/artifacts/store",
                json={"job_id": job_id, "files": {"dwg": f"output/{job_id}/drawing.dwg", "preview": f"output/{job_id}/preview.png"},
                       "metadata": {"assumptions": job.assumptions}},
            )
        except Exception as e:
            logger.warning("Artifact storage failed (continuing): %s", e)

        job.status = JobStatus.completed
        job.next_action = f"/job/{job_id}/artifacts"
        self.store.jobs[job_id] = job
        return job


    def create_job_sync(self, req: CreateJobRequest) -> JobResponse:
        return asyncio.run(self.create_job(req))

    def get_job(self, job_id: str) -> JobResponse | None:
        return self.store.jobs.get(job_id)
