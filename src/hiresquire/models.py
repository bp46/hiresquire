"""Pydantic v2 models — single source of truth for SDK, CLI, and MCP schemas.

All request/response shapes are defined here so there is one canonical source
for field names, validation constraints, and docstrings across every surface.
"""

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ResumeInput(BaseModel):
    filename: str = Field(..., description="Original filename, e.g. 'resume.pdf'")
    content: str = Field(..., description="Raw extracted text (priority 1)")
    base64: Optional[str] = Field(None, description="Base64-encoded file (priority 2)")
    file_url: Optional[str] = Field(None, description="Public HTTPS URL (priority 3)")


class WebhookConditions(BaseModel):
    min_score: Optional[int] = Field(None, ge=0, le=100)
    only_top_n: Optional[int] = Field(None, ge=1, le=100)
    events: Optional[List[str]] = None


class CreateJobRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Job posting title")
    description: str = Field(..., min_length=50, description="Job description (min 50 chars)")
    resumes: List[ResumeInput] = Field(..., min_length=1, max_length=100)
    leniency_level: int = Field(5, ge=1, le=10, description="1=lenient, 10=strict")
    custom_instructions: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_conditions: Optional[WebhookConditions] = None
    idempotency_key: Optional[str] = None


class CreateJobFromZipRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=50)
    zip_path: str
    leniency_level: int = Field(5, ge=1, le=10)
    custom_instructions: Optional[str] = None
    webhook_url: Optional[str] = None
    idempotency_key: Optional[str] = None


class GenerateEmailRequest(BaseModel):
    candidate_id: int
    type: str = Field("invite", pattern="^(invite|rejection|keep-warm|followup)$")
    tone: str = Field("professional", pattern="^(professional|friendly|formal)$")
    custom_message: Optional[str] = None
    custom_notes: Optional[str] = None


class BulkGenerateEmailsRequest(BaseModel):
    candidate_ids: List[int] = Field(..., min_length=1, max_length=50)
    type: str = Field(..., pattern="^(invite|rejection|keep-warm|followup)$")
    tone: str = Field("professional", pattern="^(professional|friendly|formal)$")


class ReportOutcomeRequest(BaseModel):
    candidate_id: int
    outcome: str = Field(..., pattern="^(hired|rejected|withdrawn)$")


class UpdateCandidateStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(pending|shortlisted|rejected|interviewed|offered|hired)$")


class PurchaseCreditsRequest(BaseModel):
    amount: Optional[float] = Field(None, ge=5)
    pack: Optional[str] = Field(None, pattern="^(pouch|satchel|chest)$")
    payment_method_id: str


class EnableAutoReloadRequest(BaseModel):
    threshold: float = Field(..., ge=1, le=1000)
    amount: float = Field(..., ge=5, le=1000)
    payment_method_id: str


class CreateCalendarConnectionRequest(BaseModel):
    provider: str = Field(..., pattern="^(calendly|calcom)$")
    api_key: str
    calendar_id: Optional[str] = None


class CreateInterviewRequest(BaseModel):
    job_id: int
    candidate_id: int
    scheduled_at: str  # ISO 8601
    duration_minutes: int = Field(60, ge=15, le=480)
    provider: Optional[str] = Field(None, pattern="^(calendly|calcom)$")


class CreateMeetingLinkRequest(BaseModel):
    provider: str = Field(..., pattern="^(calendly|calcom)$")
    topic: str
    duration: int = Field(60, ge=15, le=480)


class GenerateMeetingLinkRequest(BaseModel):
    provider: str = Field(..., pattern="^(calendly|calcom)$")
    topic: str
    duration: int = Field(60, ge=15, le=480)


class CreateAgentKeyRequest(BaseModel):
    name: str
    monthly_spend_limit: Optional[float] = None
    daily_spend_limit: Optional[float] = None
    lifetime_spend_limit: Optional[float] = None
    permissions: Optional[List[str]] = None


class UpdateAgentKeyRequest(BaseModel):
    name: Optional[str] = None
    monthly_spend_limit: Optional[float] = None
    daily_spend_limit: Optional[float] = None
    lifetime_spend_limit: Optional[float] = None


class EstimateCostRequest(BaseModel):
    candidate_count: int = Field(..., ge=1, le=100)


class TestWebhookRequest(BaseModel):
    url: str


class AuditScreeningJobRequest(BaseModel):
    job_id: int
    selection_threshold: int = Field(70, ge=1, le=100)


class ListJobsRequest(BaseModel):
    status: Optional[str] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(10, ge=1, le=100)


class GetCreditTransactionsRequest(BaseModel):
    limit: int = Field(50, ge=1, le=1000)
    offset: int = Field(0, ge=0)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    job_id: int
    status: str
    status_url: Optional[str] = None
    results_url: Optional[str] = None
    message: Optional[str] = None


class JobStatus(BaseModel):
    job_id: int
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None
    completed_at: Optional[str] = None


class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None


class Candidate(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    score: int
    summary: Optional[str] = ""
    strengths: List[str] = []
    weaknesses: List[str] = []
    interview_questions: List[Any] = []
    match_explanation: Optional[str] = None
    decision_rationale: Optional[str] = None
    experience_years: Optional[int] = None
    education: Optional[str] = None
    skills: List[str] = []
    contact_info: Optional[ContactInfo] = None
    status: str = "new"
    processed_at: Optional[str] = None


class ResultsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    job_id: int
    job_title: Optional[str] = None
    title: Optional[str] = None
    status: str
    total_candidates: int = 0
    candidates: List[Candidate] = []
    agent_summary: Optional[str] = None
    screened_at: Optional[str] = None
    has_more: bool = False

    @model_validator(mode="after")
    def _sync_titles(self) -> "ResultsResponse":
        if self.job_title is None and self.title is not None:
            self.job_title = self.title
        elif self.title is None and self.job_title is not None:
            self.title = self.job_title
        return self


class JobListItem(BaseModel):
    id: int
    title: str
    status: str
    total_candidates: int
    created_at: str
    completed_at: Optional[str] = None


class JobsListResponse(BaseModel):
    jobs: List[JobListItem]
    total: int
    page: int
    per_page: int


class EmailResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    candidate_id: int
    candidate_name: Optional[str] = None
    email_type: Optional[str] = None
    subject: str = ""
    body: str = ""
    generated_at: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _unwrap_nested_email(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("email"), dict):
            merged = dict(data)
            nested = merged["email"]
            merged.setdefault("subject", nested.get("subject", ""))
            merged.setdefault("body", nested.get("body", ""))
            return merged
        return data


class CancelJobResponse(BaseModel):
    job_id: int
    status: str
    message: str


class CompareCandidate(BaseModel):
    id: int
    name: str
    score: int
    summary: str


class CompareResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    job_id: int
    compared_count: Optional[int] = None
    top_candidate: Optional[str] = None
    top_score: Optional[int] = None
    score_range: Optional[int] = None
    candidates: List[CompareCandidate] = []
    delta_analysis: Optional[Any] = None
    comparison: Optional[dict] = None


class OutcomeResponse(BaseModel):
    success: bool
    message: str


class WebhookTestResponse(BaseModel):
    success: bool
    message: str
    response_code: Optional[int] = None


class RateLimitResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    limit: int
    remaining: int
    reset_at: Optional[str] = None
    reset_in_seconds: int = 0


class CandidateUpdateResponse(BaseModel):
    success: bool
    candidate: Candidate


class SchemaResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    version: str
    endpoints: List[dict] = []


class CreditBalance(BaseModel):
    balance: float
    formatted_balance: str
    total_purchased: float
    total_spent: float
    free_credits_available: int = 0
    cost_per_candidate: float
    auto_reload_enabled: bool
    auto_reload_threshold: Optional[float] = None
    auto_reload_amount: Optional[float] = None


class CreditPack(BaseModel):
    id: str
    name: str
    price: float
    credits: int
    bonus: int = 0


class CreditTransaction(BaseModel):
    id: int
    type: str
    amount: float
    balance_after: float
    description: Optional[str] = None
    candidate_count: Optional[int] = None
    cost_per_candidate: Optional[float] = None
    created_at: str


class CreditPurchaseResult(BaseModel):
    success: bool
    balance: float
    message: Optional[str] = None


class CalendarConnection(BaseModel):
    id: int
    provider: str
    status: str
    calendar_id: Optional[str] = None
    created_at: Optional[str] = None


class Interview(BaseModel):
    id: int
    job_posting_id: int
    candidate_id: int
    user_id: int
    scheduled_at: str
    duration_minutes: int
    meeting_link: Optional[str] = None
    calendar_event_id: Optional[str] = None
    status: str = "scheduled"
    provider_data: Optional[dict] = None
    created_at: str
    updated_at: str


class MeetingLinkResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    message: Optional[str] = None


class AvailableSlotsResponse(BaseModel):
    success: bool
    data: Optional[List[dict]] = None


class AgentApiKey(BaseModel):
    id: int
    name: str
    key: Optional[str] = None
    key_prefix: str
    is_active: bool
    monthly_spend_limit: Optional[float] = None
    daily_spend_limit: Optional[float] = None
    lifetime_spend_limit: Optional[float] = None
    total_spent: float = 0
    month_spent: float = 0
    day_spent: float = 0
    permissions: List[str] = []
    last_used_at: Optional[str] = None
    created_at: str


class AgentKeyUsage(BaseModel):
    total_spent: float
    month_spent: float
    day_spent: float
    monthly_spend_limit: Optional[float] = None
    daily_spend_limit: Optional[float] = None
    lifetime_spend_limit: Optional[float] = None
    remaining_monthly: Optional[float] = None
    remaining_daily: Optional[float] = None
    month_start_date: Optional[str] = None


class WhoamiCredits(BaseModel):
    model_config = ConfigDict(extra="allow")

    balance: float
    formatted_balance: str
    is_low: bool = False
    auto_reload_enabled: bool = False
    total_purchased: Optional[float] = None
    total_spent: Optional[float] = None
    cost_per_candidate: Optional[float] = None


class WhoamiResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    valid: bool
    user: dict
    credits: WhoamiCredits


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    amount: float
    expires_at: str
    pack: Optional[dict] = None
