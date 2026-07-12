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


def _ol(level) -> str:
    """Normalize output level to string."""
    return level.value if hasattr(level, 'value') else level


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
        try:
            resp = await self.client.get(f"{get_service_url(service_name)}/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def check_all_services(self) -> dict[str, bool]:
        services = ["intake", "vision", "cadplan", "validation",
                     "cad_com", "preview", "dwg_scan", "artifacts"]
        results = await asyncio.gather(*[self.check_health(s) for s in services], return_exceptions=True)
        return {s: bool(r) for s, r in zip(services, results, strict=False)}

    async def _call_service(self, service: str, path: str, payload: dict,
                             model_class, error_msg: str) -> tuple:
        """Call a service endpoint, parse response, return (data, error).

        Returns (model_instance, None) on success, (None, error_dict) on failure.
        The error dict is suitable for appending to job_resp.assumptions.
        """
        try:
            resp = await self.client.post(f"{get_service_url(service)}{path}", json=payload)
            resp.raise_for_status()
            return model_class(**resp.json()), None
        except Exception as e:
            logger.exception("%s: %%s", error_msg, e)
            return None, {"key": "error", "value": f"{error_msg}: {e}"}

    async def _call_and_store(self, service: str, path: str, payload: dict,
                               model_class, error_msg: str,
                               job_resp: JobResponse, job_id: str) -> bool:
        """Call service; on failure set job error and return False."""
        data, err = await self._call_service(service, path, payload, model_class, error_msg)
        if err:
            job_resp.status = JobStatus.error
            job_resp.next_action = "/retry"
            job_resp.assumptions.append(err)
            self.store.jobs[job_id] = job_resp
            return False
        return data


    async def create_job(self, req: CreateJobRequest) -> JobResponse:
        job_id = str(uuid.uuid4())[:8]
        job_resp = JobResponse(
            job_id=job_id,
            status=JobStatus.created,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Step 1: Intake
        intake_data = await self._call_and_store(
            "intake", "/intake/parse",
            {"user_request": req.user_request, "files": req.files, "output_level": _ol(req.output_level)},
            IntakeResponse, "Intake failed", job_resp, job_id,
        )
        if not intake_data:
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
            for fpath in req.files:
                vdata, _ = await self._call_service(
                    "vision", "/vision/analyze", {"path": fpath}, dict, "Vision failed",
                )
                if vdata:
                    job_resp.assumptions.append({"key": f"vision_{fpath}", "value": f"{len(vdata.get('lines', []))} lines"})

        # Step 2: CAD Plan
        job_resp.status = JobStatus.plan_pending
        plan_data = await self._call_and_store(
            "cadplan", "/cadplan/generate",
            {"user_request": req.user_request, "output_level": _ol(req.output_level), "unit": req.declared_unit},
            PlanResponse, "CADPlan failed", job_resp, job_id,
        )
        if not plan_data:
            return job_resp

        job_resp.assumptions.extend(plan_data.assumptions)
        self.store.plans[job_id] = plan_data

        # Step 3: Validation
        job_resp.status = JobStatus.validation_pending
        val_data = await self._call_and_store(
            "validation", "/validation/check",
            {"plan": plan_data.model_dump(), "output_level": _ol(req.output_level), "unit": req.declared_unit},
            ValidationResponse, "Validation failed", job_resp, job_id,
        )
        if not val_data:
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
            val_data, _ = await self._call_service(
                "validation", "/validation/check",
                {"plan": plan.model_dump(), "output_level": plan.output_level, "unit": plan.unit},
                ValidationResponse, "Re-validation failed",
            )
            if val_data and not val_data.valid:
                job.status = JobStatus.needs_confirmation
                job.next_action = f"/job/{job_id}/confirm"
                job.questions = val_data.blocking_questions
                self.store.jobs[job_id] = job
                return job
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
        exec_data, err = await self._call_service(
            "cad_com", "/cad_com/execute",
            {"plan": plan.model_dump(), "job_id": job_id}, dict, "CAD COM execution failed",
        )
        if err or not exec_data.get("success"):
            job.status = JobStatus.error
            job.next_action = "/retry"
            job.assumptions.append(err or {"key": "errors", "value": "; ".join(exec_data.get('errors', []))})
            self.store.jobs[job_id] = job
            return job

        # Steps 5-7: Save, Preview, Artifacts (non-critical, continue on failure)
        job.status = JobStatus.saving
        await self._call_service("cad_com", "/cad_com/save",
                                 {"path": f"output/{job_id}/drawing.dwg", "job_id": job_id}, dict, "Save failed")

        job.status = JobStatus.preview_pending
        await self._call_service("preview", "/preview/screenshot", {"job_id": job_id}, dict, "Preview failed")

        job.status = JobStatus.archiving
        await self._call_service("artifacts", "/artifacts/store",
                                 {"job_id": job_id, "files": {"dwg": f"output/{job_id}/drawing.dwg", "preview": f"output/{job_id}/preview.png"},
                                  "metadata": {"assumptions": job.assumptions}}, dict, "Artifact storage failed")

        job.status = JobStatus.completed
        job.next_action = f"/job/{job_id}/artifacts"
        self.store.jobs[job_id] = job
        return job

    def create_job_sync(self, req: CreateJobRequest) -> JobResponse:
        return asyncio.run(self.create_job(req))

    def get_job(self, job_id: str) -> JobResponse | None:
        return self.store.jobs.get(job_id)
