"""HireSquire MCP server (stdio) using FastMCP.

Exposes the full HireSquire toolkit as MCP tools, calling HireSquireClient
methods (REST endpoints) directly — no JSON-RPC proxy to /v1/mcp.

Run: hiresquire mcp   or   uvx hiresquire mcp
"""

from typing import Any, Callable, Dict, List, Optional, Union, cast

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError as PydanticValidationError

from .client import HireSquireClient
from .errors import HireSquireError
from .resume import ResumeParseError

mcp = FastMCP("HireSquire")

_client: Optional[HireSquireClient] = None


def _get_client() -> HireSquireClient:
    global _client
    if _client is None:
        _client = HireSquireClient()
    return _client


def _handle(error: Exception) -> Dict[str, Any]:
    if isinstance(error, HireSquireError):
        return {"error": error.code or "error", "message": error.message}
    if isinstance(
        error, (PydanticValidationError, ValueError, ResumeParseError, FileNotFoundError)
    ):
        return {"error": "VALIDATION_ERROR", "message": str(error)}
    return {"error": "error", "message": str(error)}


def _run(fn: Callable[[HireSquireClient], Dict[str, Any]]) -> Dict[str, Any]:
    try:
        return fn(_get_client())
    except Exception as exc:
        return _handle(exc)


# ============================================================================
# Screening tools
# ============================================================================


@mcp.tool()
def create_screening(
    title: str,
    description: str,
    resume_paths: Optional[List[str]] = None,
    resumes: Optional[List[Dict[str, str]]] = None,
    leniency_level: int = 5,
    custom_instructions: str = "",
    webhook_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Submit candidate resumes for AI screening against a job description.

    Provide either `resume_paths` (local PDF/DOCX/TXT/MD files parsed client-side)
    or `resumes` (pre-parsed {filename, content} dicts).
    """

    def _call(client: HireSquireClient) -> Dict[str, Any]:
        resume_objects: List[Dict[str, str]] = []
        if resume_paths:
            from .resume import read_resumes_from_paths

            resume_objects.extend(read_resumes_from_paths(resume_paths))
        if resumes:
            resume_objects.extend(resumes)
        if not resume_objects:
            return {"error": "VALIDATION_ERROR", "message": "No resumes provided"}
        return client.jobs.create(
            title,
            description,
            cast(List[Union[str, Dict[str, str]]], resume_objects),
            leniency_level=leniency_level,
            custom_instructions=custom_instructions,
            webhook_url=webhook_url,
        )

    return _run(_call)


@mcp.tool()
def get_screening_status(job_id: int) -> Dict[str, Any]:
    """Check the processing status of a screening job."""
    return _run(lambda c: c.jobs.get_status(job_id))


@mcp.tool()
def get_results(job_id: int, min_score: int = 0, only_top_n: int = 0) -> Dict[str, Any]:
    """Retrieve candidate scores and summaries for a completed job."""
    return _run(
        lambda c: c.jobs.get_results(
            job_id, min_score=min_score or None, only_top_n=only_top_n or None
        )
    )


@mcp.tool()
def cancel_screening_job(job_id: int) -> Dict[str, Any]:
    """Cancel a running screening job."""
    return _run(lambda c: c.jobs.cancel(job_id))


@mcp.tool()
def compare_candidates(job_id: int, candidate_ids: List[int]) -> Dict[str, Any]:
    """Compare candidates side-by-side with delta analysis."""
    return _run(lambda c: c.jobs.compare(job_id, candidate_ids))


@mcp.tool()
def report_hiring_outcome(job_id: int, candidate_id: int, outcome: str) -> Dict[str, Any]:
    """Report the final hiring decision (hired/rejected/withdrawn)."""
    return _run(lambda c: c.jobs.report_outcome(job_id, candidate_id, outcome))


# ============================================================================
# Email tools
# ============================================================================


@mcp.tool()
def generate_email(
    job_id: int,
    candidate_id: int,
    email_type: str = "invite",
    tone: str = "professional",
    custom_notes: str = "",
) -> Dict[str, Any]:
    """Generate a personalized outreach email for a candidate."""
    return _run(lambda c: c.emails.generate(job_id, candidate_id, email_type, tone, custom_notes))


@mcp.tool()
def bulk_generate_emails(
    job_id: int, candidate_ids: List[int], email_type: str = "invite", tone: str = "professional"
) -> Dict[str, Any]:
    """Generate multiple candidate emails in a single call (max 50)."""
    return _run(lambda c: c.emails.bulk_generate(job_id, candidate_ids, email_type, tone))


# ============================================================================
# Credits tools
# ============================================================================


@mcp.tool()
def get_credit_balance() -> Dict[str, Any]:
    """Check current credit balance."""
    return _run(lambda c: c.credits.get_balance())


@mcp.tool()
def estimate_screening_cost(candidate_count: int) -> Dict[str, Any]:
    """Estimate credit cost for screening N candidates."""
    return _run(lambda c: c.credits.estimate_cost(candidate_count))


@mcp.tool()
def list_credit_packs() -> Dict[str, Any]:
    """List available credit packs."""
    return _run(lambda c: c.credits.list_packs())


@mcp.tool()
def get_credit_transactions(limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    """Fetch credit transaction history."""
    return _run(lambda c: c.credits.get_transactions(limit=limit, offset=offset))


@mcp.tool()
def purchase_credits(
    amount: Optional[float] = None, pack: Optional[str] = None, payment_method_id: str = ""
) -> Dict[str, Any]:
    """Purchase credits using a saved payment method."""
    return _run(
        lambda c: c.credits.purchase(amount=amount, pack=pack, payment_method_id=payment_method_id)
    )


@mcp.tool()
def create_checkout_session(
    amount: Optional[float] = None, pack: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a Stripe Checkout URL for manual credit purchase."""
    return _run(lambda c: c.credits.create_checkout_session(amount=amount, pack=pack))


@mcp.tool()
def enable_auto_reload(threshold: float, amount: float, payment_method_id: str) -> Dict[str, Any]:
    """Enable automatic credit reloading below a threshold."""
    return _run(lambda c: c.credits.enable_auto_reload(threshold, amount, payment_method_id))


@mcp.tool()
def disable_auto_reload() -> Dict[str, Any]:
    """Disable automatic credit reloading."""
    return _run(lambda c: c.credits.disable_auto_reload())


# ============================================================================
# Calendar & interview tools
# ============================================================================


@mcp.tool()
def list_calendar_connections() -> Dict[str, Any]:
    """List connected calendar providers."""
    return _run(lambda c: c.calendar.list())


@mcp.tool()
def create_calendar_connection(
    provider: str, api_key: str, calendar_id: Optional[str] = None
) -> Dict[str, Any]:
    """Connect a calendar provider (calendly/calcom)."""
    return _run(lambda c: c.calendar.connect(provider, api_key, calendar_id))


@mcp.tool()
def get_available_slots(provider: str, date: str, duration: int = 60) -> Dict[str, Any]:
    """Get available interview slots for a date."""
    return _run(lambda c: c.calendar.get_slots(provider, date, duration))


@mcp.tool()
def create_interview(
    job_id: int,
    candidate_id: int,
    scheduled_at: str,
    duration_minutes: int = 60,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Schedule an interview and create a calendar event."""
    return _run(
        lambda c: c.calendar.create_interview(
            job_id, candidate_id, scheduled_at, duration_minutes, provider
        )
    )


@mcp.tool()
def generate_meeting_link(provider: str, topic: str, duration: int = 60) -> Dict[str, Any]:
    """Generate a one-off meeting link."""
    return _run(lambda c: c.calendar.generate_meeting_link(provider, topic, duration))


# ============================================================================
# Utility tools
# ============================================================================


@mcp.tool()
def whoami() -> Dict[str, Any]:
    """Verify token validity and get profile/balance info (free health check)."""
    return _run(lambda c: c.utils.whoami())


@mcp.tool()
def get_rate_limit() -> Dict[str, Any]:
    """Get current API rate limit status."""
    return _run(lambda c: c.utils.get_rate_limit())


@mcp.tool()
def test_webhook(url: str) -> Dict[str, Any]:
    """Test a webhook endpoint."""
    return _run(lambda c: c.utils.test_webhook(url))


@mcp.tool()
def get_api_schema() -> Dict[str, Any]:
    """Fetch the full OpenAPI schema."""
    return _run(lambda c: c.utils.get_api_schema())


@mcp.tool()
def audit_screening_job(job_id: int, selection_threshold: int = 70) -> Dict[str, Any]:
    """Run an automated bias & disparate impact audit for a screening job."""
    return _run(lambda c: c.utils.audit_screening_job(job_id, selection_threshold))


def main() -> None:
    """Entry point for the `hiresquire-mcp` console script."""
    mcp.run()


if __name__ == "__main__":
    main()
