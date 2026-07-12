"""GatewayEngine — HTTP-based microservice orchestration for CAD jobs."""
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


class OrchestratorEngine:
    """Coordinate the full job lifecycle via HTTP calls to microservices."""

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

        job_resp = JobResponse(
            job_id=job_id,
            status=JobStatus.created,
            created_at=created_at,
        )

        # --- Step 1: Intake via HTTP ---
        try:
            intake_url = f"{get_service_url('intake')}/intake/parse"
            intake_payload = {
                "user_request": req.user_request,
                "files": req.files,
                "output_level": req.output_level.value if hasattr(req.output_level, 'value') else req.output_level,
            }
            intake_resp = await self.client.post(intake_url, json=intake_payload)
            intake_resp.raise_for_status()
            intake_data = IntakeResponse(**intake_resp.json())
        except Exception as e:
            logger.exception("Intake service call failed")
            job_resp.status = JobStatus.error
            job_resp.next_action = "/retry"
            job_resp.assumptions = [{"key": "error", "value": f"Intake failed: {e}"}]
            self.store.jobs[job_id] = job_resp
            return job_resp

        job_resp.status = JobStatus.intake
        job_resp.assumptions = [
            {"key": "intent", "value": intake_data.intent},
            {"key": "unit", "value": intake_data.unit},
            {"key": "input_type", "value": intake_data.input_type},
        ]
        if intake_data.needs_more_info:
            job_resp.next_action = "/job/confirm"
            job_resp.questions = ["Please provide more details about what you want to draw."]
            self.store.jobs[job_id] = job_resp
            return job_resp

        # --- Step 2: CAD Plan via HTTP ---
        try:
            cadplan_url = f"{get_service_url('cadplan')}/cadplan/generate"
            cadplan_payload = {
                "user_request": req.user_request,
                "output_level": req.output_level.value if hasattr(req.output_level, 'value') else req.output_level,
                "unit": req.declared_unit,
            }
            cadplan_resp = await self.client.post(cadplan_url, json=cadplan_payload)
            cadplan_resp.raise_for_status()
            plan_data = PlanResponse(**cadplan_resp.json())
        except Exception as e:
            logger.exception("CADPlan service call failed")
            job_resp.status = JobStatus.error
            job_resp.next_action = "/retry"
            job_resp.assumptions.append({"key": "error", "value": f"CADPlan failed: {e}"})
            self.store.jobs[job_id] = job_resp
            return job_resp

        job_resp.status = JobStatus.planning
        job_resp.assumptions.extend(plan_data.assumptions)

        # --- Step 3: Validation via HTTP ---
        try:
            val_url = f"{get_service_url('validation')}/validation/check"
            val_payload = {
                "plan": plan_data.model_dump(),
                "output_level": req.output_level.value if hasattr(req.output_level, 'value') else req.output_level,
                "unit": req.declared_unit,
            }
            val_resp = await self.client.post(val_url, json=val_payload)
            val_resp.raise_for_status()
            val_data = ValidationResponse(**val_resp.json())
        except Exception as e:
            logger.exception("Validation service call failed")
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
            job_resp.next_action = "/cad_com/execute"

        self.store.jobs[job_id] = job_resp
        return job_resp

    async def execute_plan(self, job_id: str, plan: PlanResponse) -> JobResponse | None:
        job = self.store.jobs.get(job_id)
        if job is None:
            return None

        try:
            com_url = f"{get_service_url('cad_com')}/cad_com/execute"
            com_payload = {
                "plan": plan.model_dump(),
                "job_id": job_id,
            }
            com_resp = await self.client.post(com_url, json=com_payload)
            com_resp.raise_for_status()
            exec_data = com_resp.json()
        except Exception as e:
            logger.exception("CAD COM execution failed")
            job.status = JobStatus.error
            job.next_action = "/retry"
            job.assumptions.append({"key": "error", "value": f"Execution failed: {e}"})
            self.store.jobs[job_id] = job
            return job

        if exec_data.get("success"):
            job.status = JobStatus.executing
            job.next_action = "/preview/generate"
        else:
            job.status = JobStatus.error
            job.next_action = "/retry"
            errors = exec_data.get("errors", [])
            job.assumptions.append({"key": "execution_errors", "value": "; ".join(errors)})

        self.store.jobs[job_id] = job
        return job

    def create_job_sync(self, req: CreateJobRequest) -> JobResponse:
        return asyncio.run(self.create_job(req))

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
