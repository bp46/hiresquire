"""HireSquireClient — unified SDK client with namespaces.

All surfaces (SDK, CLI, MCP) delegate to this client. Method signatures accept
and return Pydantic models defined in :mod:`hiresquire.models`.
"""

import os
import time
from typing import Any, Dict, List, Optional, Type, Union, cast

from .config import Config
from .errors import HireSquireError
from .http import HttpClient, generate_idempotency_key
from .models import (
    BulkGenerateEmailsRequest,
    CancelJobResponse,
    CompareResponse,
    CreateAgentKeyRequest,
    CreateCalendarConnectionRequest,
    CreateInterviewRequest,
    CreateJobRequest,
    CreateMeetingLinkRequest,
    CreditBalance,
    CreditPurchaseResult,
    EmailResponse,
    EnableAutoReloadRequest,
    GenerateEmailRequest,
    JobResponse,
    JobStatus,
    OutcomeResponse,
    PurchaseCreditsRequest,
    RateLimitResponse,
    ReportOutcomeRequest,
    ResultsResponse,
    ResumeInput,
    SchemaResponse,
    TestWebhookRequest,
    UpdateAgentKeyRequest,
    UpdateCandidateStatusRequest,
    WebhookConditions,
    WebhookTestResponse,
    WhoamiResponse,
)
from .resume import read_resume_from_file, read_resumes_from_paths


class _NamespaceBase:
    def __init__(self, client: "HireSquireClient"):
        self._client = client


class JobsNamespace(_NamespaceBase):
    def create(
        self,
        title: str,
        description: str,
        resumes: List[Union[str, Dict[str, str]]],
        leniency_level: int = 5,
        custom_instructions: str = "",
        webhook_url: Optional[str] = None,
        webhook_conditions: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a screening job. Resumes may be file paths or content dicts."""
        resume_objects = self._prepare_resumes(resumes)
        wh = WebhookConditions(**webhook_conditions) if webhook_conditions else None
        ikey = idempotency_key or generate_idempotency_key()
        payload = CreateJobRequest(
            title=title,
            description=description,
            resumes=resume_objects,
            leniency_level=leniency_level,
            custom_instructions=custom_instructions or None,
            webhook_url=webhook_url,
            webhook_conditions=wh,
            idempotency_key=ikey,
        )
        resp = self._client.http.post(
            "jobs",
            json=payload.model_dump(mode="json", exclude_none=True),
            idempotency_key=ikey,
        )
        return JobResponse.model_validate(resp.json()).model_dump(mode="json")

    def create_from_zip(
        self,
        title: str,
        description: str,
        zip_path: str,
        leniency_level: int = 5,
        custom_instructions: str = "",
        webhook_url: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a screening job by uploading a ZIP of resumes."""
        data: Dict[str, Any] = {
            "title": title,
            "description": description,
            "leniency_level": str(leniency_level),
        }
        if custom_instructions:
            data["custom_instructions"] = custom_instructions
        if webhook_url:
            data["webhook_url"] = webhook_url
        ikey = idempotency_key or generate_idempotency_key()
        with open(zip_path, "rb") as f:
            files = {"zip_file": ("resumes.zip", f, "application/zip")}
            resp = self._client.http.post(
                "jobs/upload-zip",
                data=data,
                files=files,
                idempotency_key=ikey,
                timeout=120,
            )
        return JobResponse.model_validate(resp.json()).model_dump(mode="json")

    def list(
        self,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 10,
    ) -> Dict[str, Any]:
        """List screening jobs."""
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if status is not None:
            params["status"] = status
        resp = self._client.http.get("jobs", params=params)
        return cast(Dict[str, Any], resp.json())

    def get_status(self, job_id: int) -> Dict[str, Any]:
        resp = self._client.http.get(f"jobs/{job_id}")
        return JobStatus.model_validate(resp.json()).model_dump(mode="json")

    def get_results(
        self,
        job_id: int,
        min_score: Optional[int] = None,
        only_top_n: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if min_score is not None:
            params["min_score"] = min_score
        if only_top_n is not None:
            params["only_top_n"] = only_top_n
        resp = self._client.http.get(f"jobs/{job_id}/results", params=params)
        return ResultsResponse.model_validate(resp.json()).model_dump(mode="json")

    def wait(
        self,
        job_id: int,
        poll_interval: int = 3,
        max_wait_seconds: int = 300,
    ) -> Dict[str, Any]:
        start = time.time()
        while time.time() - start < max_wait_seconds:
            status = self.get_status(job_id)
            if status["status"] == "completed":
                return self.get_results(job_id)
            if status["status"] == "failed":
                raise HireSquireError(f"Screening job {job_id} failed", status_code=500)
            time.sleep(poll_interval)
        raise TimeoutError(f"Job {job_id} did not complete within {max_wait_seconds} seconds")

    def cancel(self, job_id: int) -> Dict[str, Any]:
        resp = self._client.http.post(f"jobs/{job_id}/cancel")
        return CancelJobResponse.model_validate(resp.json()).model_dump(mode="json")

    def compare(self, job_id: int, candidate_ids: List[int]) -> Dict[str, Any]:
        resp = self._client.http.get(
            f"jobs/{job_id}/compare", params={"ids": ",".join(map(str, candidate_ids))}
        )
        return CompareResponse.model_validate(resp.json()).model_dump(mode="json")

    def report_outcome(
        self,
        job_id: int,
        candidate_id: int,
        outcome: str,
    ) -> Dict[str, Any]:
        payload = ReportOutcomeRequest(candidate_id=candidate_id, outcome=outcome)
        resp = self._client.http.post(
            f"jobs/{job_id}/outcome", json=payload.model_dump(mode="json")
        )
        return OutcomeResponse.model_validate(resp.json()).model_dump(mode="json")

    def _prepare_resumes(self, resumes: List[Union[str, Dict[str, str]]]) -> List[ResumeInput]:
        objects: List[ResumeInput] = []
        for resume in resumes:
            if isinstance(resume, str) and os.path.exists(resume):
                data = read_resume_from_file(resume)
                objects.append(
                    ResumeInput(
                        filename=data["filename"],
                        content=data["content"],
                        base64=None,
                        file_url=None,
                    )
                )
            elif isinstance(resume, dict) and "filename" in resume and "content" in resume:
                objects.append(
                    ResumeInput(
                        filename=resume["filename"],
                        content=resume["content"],
                        base64=resume.get("base64"),
                        file_url=resume.get("file_url"),
                    )
                )
            else:
                raise ValueError(
                    f"Invalid resume ({type(resume).__name__}). Must be an existing file path or "
                    "dict with 'filename' and 'content'."
                )
        return objects


class CandidatesNamespace(_NamespaceBase):
    def get(self, candidate_id: int) -> Dict[str, Any]:
        resp = self._client.http.get(f"candidates/{candidate_id}")
        return cast(Dict[str, Any], resp.json())

    def update_status(self, candidate_id: int, status: str) -> Dict[str, Any]:
        payload = UpdateCandidateStatusRequest(status=status)
        resp = self._client.http.patch(
            f"candidates/{candidate_id}/status", json=payload.model_dump(mode="json")
        )
        return cast(Dict[str, Any], resp.json())

    def generate_email(
        self,
        job_id: int,
        candidate_id: int,
        email_type: str = "invite",
        tone: str = "professional",
        custom_notes: str = "",
    ) -> Dict[str, Any]:
        """Deprecated v1 location; delegates to client.emails.generate()."""
        return self._client.emails.generate(
            job_id, candidate_id, email_type=email_type, tone=tone, custom_notes=custom_notes
        )

    def compare(self, candidates: List[Dict[str, Any]], candidate_ids: List[int]) -> Dict[str, Any]:
        """Local candidate comparison (v1 compatibility)."""
        from .utils import compare_candidates

        return compare_candidates(candidates, candidate_ids)


class CreditsNamespace(_NamespaceBase):
    def get_balance(self) -> Dict[str, Any]:
        resp = self._client.http.get("credits/balance")
        return CreditBalance.model_validate(resp.json()).model_dump(mode="json")

    def estimate_cost(self, candidate_count: int) -> Dict[str, Any]:
        resp = self._client.http.get(
            "credits/estimate", params={"candidate_count": candidate_count}
        )
        return cast(Dict[str, Any], resp.json())

    def list_packs(self) -> Dict[str, Any]:
        resp = self._client.http.get("credits/packs")
        return cast(Dict[str, Any], resp.json())

    def get_transactions(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        resp = self._client.http.get(
            "credits/transactions", params={"limit": limit, "offset": offset}
        )
        return cast(Dict[str, Any], resp.json())

    def purchase(
        self,
        amount: Optional[float] = None,
        pack: Optional[str] = None,
        payment_method_id: str = "",
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = PurchaseCreditsRequest(
            amount=amount, pack=pack, payment_method_id=payment_method_id
        )
        ikey = idempotency_key or generate_idempotency_key()
        resp = self._client.http.post(
            "credits/purchase",
            json=payload.model_dump(mode="json", exclude_none=True),
            idempotency_key=ikey,
        )
        return CreditPurchaseResult.model_validate(resp.json()).model_dump(mode="json")

    def create_payment_intent(
        self,
        amount: float,
        payment_method_id: Optional[str] = None,
        return_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {"amount": amount}
        if payment_method_id:
            data["payment_method_id"] = payment_method_id
        if return_url:
            data["return_url"] = return_url
        resp = self._client.http.post("credits/payment-intent", json=data)
        return cast(Dict[str, Any], resp.json())

    def create_checkout_session(
        self, amount: Optional[float] = None, pack: Optional[str] = None
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        if pack:
            data["pack"] = pack
        elif amount is not None:
            data["amount"] = amount
        else:
            data["pack"] = "pouch"
        resp = self._client.http.post("credits/checkout", json=data)
        return cast(Dict[str, Any], resp.json())

    def enable_auto_reload(
        self, threshold: float, amount: float, payment_method_id: str
    ) -> Dict[str, Any]:
        payload = EnableAutoReloadRequest(
            threshold=threshold, amount=amount, payment_method_id=payment_method_id
        )
        resp = self._client.http.post(
            "credits/auto-reload/enable", json=payload.model_dump(mode="json")
        )
        return cast(Dict[str, Any], resp.json())

    def disable_auto_reload(self) -> Dict[str, Any]:
        resp = self._client.http.post("credits/auto-reload/disable")
        return cast(Dict[str, Any], resp.json())


class CalendarNamespace(_NamespaceBase):
    def list(self) -> Dict[str, Any]:
        resp = self._client.http.get("calendar/connections")
        return cast(Dict[str, Any], resp.json())

    def connect(
        self, provider: str, api_key: str, calendar_id: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = CreateCalendarConnectionRequest(
            provider=provider, api_key=api_key, calendar_id=calendar_id
        )
        resp = self._client.http.post("calendar/connections", json=payload.model_dump(mode="json"))
        return cast(Dict[str, Any], resp.json())

    def get_slots(self, provider: str, date: str, duration: int = 60) -> Dict[str, Any]:
        resp = self._client.http.get(
            "calendar/slots", params={"provider": provider, "date": date, "duration": duration}
        )
        return cast(Dict[str, Any], resp.json())

    def create_interview(
        self,
        job_id: int,
        candidate_id: int,
        scheduled_at: str,
        duration_minutes: int = 60,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = CreateInterviewRequest(
            job_id=job_id,
            candidate_id=candidate_id,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            provider=provider,
        )
        resp = self._client.http.post("interviews", json=payload.model_dump(mode="json"))
        return cast(Dict[str, Any], resp.json())

    def generate_meeting_link(
        self, provider: str, topic: str, duration: int = 60
    ) -> Dict[str, Any]:
        payload = CreateMeetingLinkRequest(provider=provider, topic=topic, duration=duration)
        resp = self._client.http.post("meetings/links", json=payload.model_dump(mode="json"))
        return cast(Dict[str, Any], resp.json())

    def generate_link(self, provider: str, topic: str, duration: int = 60) -> Dict[str, Any]:
        """v1 compatibility alias for generate_meeting_link()."""
        return self.generate_meeting_link(provider, topic, duration)


class AgentKeysNamespace(_NamespaceBase):
    def list(self) -> Dict[str, Any]:
        resp = self._client.http.get("agent-keys")
        return cast(Dict[str, Any], resp.json())

    def create(
        self,
        name: str,
        monthly_spend_limit: Optional[float] = None,
        daily_spend_limit: Optional[float] = None,
        lifetime_spend_limit: Optional[float] = None,
        permissions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        payload = CreateAgentKeyRequest(
            name=name,
            monthly_spend_limit=monthly_spend_limit,
            daily_spend_limit=daily_spend_limit,
            lifetime_spend_limit=lifetime_spend_limit,
            permissions=permissions,
        )
        resp = self._client.http.post("agent-keys", json=payload.model_dump(mode="json"))
        return cast(Dict[str, Any], resp.json())

    def get(self, key_id: int) -> Dict[str, Any]:
        resp = self._client.http.get(f"agent-keys/{key_id}")
        return cast(Dict[str, Any], resp.json())

    def update(self, key_id: int, **kwargs: Any) -> Dict[str, Any]:
        payload = UpdateAgentKeyRequest(**kwargs)
        resp = self._client.http.put(
            f"agent-keys/{key_id}",
            json=payload.model_dump(mode="json", exclude_unset=True),
        )
        return cast(Dict[str, Any], resp.json())

    def revoke(self, key_id: int) -> Dict[str, Any]:
        resp = self._client.http.delete(f"agent-keys/{key_id}")
        return cast(Dict[str, Any], resp.json())

    def regenerate(self, key_id: int) -> Dict[str, Any]:
        resp = self._client.http.post(f"agent-keys/{key_id}/regenerate")
        return cast(Dict[str, Any], resp.json())

    def get_usage(self, key_id: int) -> Dict[str, Any]:
        resp = self._client.http.get(f"agent-keys/{key_id}/usage")
        return cast(Dict[str, Any], resp.json())


class EmailsNamespace(_NamespaceBase):
    def generate(
        self,
        job_id: int,
        candidate_id: int,
        email_type: str = "invite",
        tone: str = "professional",
        custom_notes: str = "",
    ) -> Dict[str, Any]:
        payload = GenerateEmailRequest(
            candidate_id=candidate_id,
            type=email_type,
            tone=tone,
            custom_notes=custom_notes or None,
        )
        resp = self._client.http.post(
            f"jobs/{job_id}/generate-email",
            json=payload.model_dump(mode="json", exclude_none=True),
        )
        return EmailResponse.model_validate(resp.json()).model_dump(mode="json")

    def generate_questions(self, job_id: int, candidate_id: int, count: int = 5) -> Dict[str, Any]:
        resp = self._client.http.post(
            f"jobs/{job_id}/generate-questions",
            json={"candidate_id": candidate_id, "count": count},
        )
        return cast(Dict[str, Any], resp.json())

    def generate_icebreaker(self, job_id: int, candidate_id: int) -> Dict[str, Any]:
        resp = self._client.http.post(
            f"jobs/{job_id}/generate-icebreaker", json={"candidate_id": candidate_id}
        )
        return cast(Dict[str, Any], resp.json())

    def bulk_generate(
        self,
        job_id: int,
        candidate_ids: List[int],
        email_type: str = "invite",
        tone: str = "professional",
    ) -> Dict[str, Any]:
        payload = BulkGenerateEmailsRequest(candidate_ids=candidate_ids, type=email_type, tone=tone)
        resp = self._client.http.post(
            f"jobs/{job_id}/bulk-generate-emails", json=payload.model_dump(mode="json")
        )
        return cast(Dict[str, Any], resp.json())


class UtilsNamespace(_NamespaceBase):
    def whoami(self) -> Dict[str, Any]:
        resp = self._client.http.get("schema/validate")
        return WhoamiResponse.model_validate(resp.json()).model_dump(mode="json")

    def get_rate_limit(self) -> Dict[str, Any]:
        resp = self._client.http.get("rate-limit")
        return RateLimitResponse.model_validate(resp.json()).model_dump(mode="json")

    def test_webhook(self, url: str) -> Dict[str, Any]:
        payload = TestWebhookRequest(url=url)
        resp = self._client.http.post("webhooks/test", json=payload.model_dump(mode="json"))
        return WebhookTestResponse.model_validate(resp.json()).model_dump(mode="json")

    def get_api_schema(self) -> Dict[str, Any]:
        resp = self._client.http.get("schema")
        return SchemaResponse.model_validate(resp.json()).model_dump(mode="json")

    def audit_screening_job(self, job_id: int, selection_threshold: int = 70) -> Dict[str, Any]:
        resp = self._client.http.post(
            f"jobs/{job_id}/audit", json={"selection_threshold": selection_threshold}
        )
        return cast(Dict[str, Any], resp.json())


class HireSquireClient:
    """HireSquire SDK client.

    Example::

        client = HireSquireClient("YOUR_API_TOKEN")
        job = client.jobs.create("Senior Developer", "...", ["resume1.pdf"])
        results = client.jobs.wait(job["job_id"])
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
        base_url: Optional[str] = None,
        config: Optional[Config] = None,
        timeout: float = 30.0,
    ):
        cfg = config or Config.load()
        self.api_token = api_token or cfg.api_token
        self.base_url = base_url or cfg.base_url
        self.http = HttpClient(
            api_token=self.api_token, base_url=self.base_url, config=cfg, timeout=timeout
        )

        # Namespaces
        self.jobs = JobsNamespace(self)
        self.candidates = CandidatesNamespace(self)
        self.credits = CreditsNamespace(self)
        self.calendar = CalendarNamespace(self)
        self.agent_keys = AgentKeysNamespace(self)
        self.emails = EmailsNamespace(self)
        self.utils = UtilsNamespace(self)

    # Shortcut methods mirroring v1 `HireSquire` API
    def whoami(self) -> Dict[str, Any]:
        """Verify API token and get profile info (shortcut for utils.whoami)."""
        return self.utils.whoami()

    def screen(
        self,
        title: str,
        description: str,
        resumes: List[Union[str, Dict[str, str]]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Submit a screening job and return the job object (shortcut for jobs.create)."""
        return self.jobs.create(title, description, resumes, **kwargs)

    def wait_for_completion(self, job_id: int, **kwargs: Any) -> Dict[str, Any]:
        """Poll until job completes and return results (shortcut for jobs.wait)."""
        return self.jobs.wait(job_id, **kwargs)

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> "HireSquireClient":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[object],
    ) -> None:
        self.close()

    # Resume parsing helpers exposed for convenience
    def read_resume_from_file(self, file_path: str) -> Dict[str, str]:
        return read_resume_from_file(file_path)

    def read_resumes_from_paths(self, paths: List[str]) -> List[Dict[str, str]]:
        return read_resumes_from_paths(paths)
