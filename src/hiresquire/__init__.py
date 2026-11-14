"""HireSquire — AI-Powered Candidate Screening SDK (v2).

Unified package exposing the Python SDK, CLI, and MCP server from a single
install::

    pip install hiresquire

Quick start::

    from hiresquire import HireSquireClient

    client = HireSquireClient("YOUR_API_TOKEN")
    job = client.jobs.create("Senior Developer", "...", ["resume1.pdf"])
    results = client.jobs.wait(job["job_id"])

Backward-compatible v1 import path::

    from hiresquire import HireSquire  # alias for HireSquireClient
    from hiresquire import create_screening_job  # deprecated v1 wrapper

Environment variables:
    HIRESQUIRE_API_TOKEN   Your API token (or ~/.hiresquire/config.json)
    HIRESQUIRE_BASE_URL    API base URL (default: https://hiresquireai.com/api/v1)
"""

import warnings
from typing import Any, Dict, List, Optional, Union

from .__version__ import __version__
from .client import HireSquireClient
from .config import Config
from .errors import HireSquireError
from .http import HttpClient, generate_idempotency_key
from .resume import read_resume_from_file, read_resumes_from_paths

# Public API
HireSquire = HireSquireClient  # v1 backward-compatible alias


# ---------------------------------------------------------------------------
# Deprecated v1 top-level function wrappers
# ---------------------------------------------------------------------------


def _v1_warning(func_name: str) -> None:
    warnings.warn(
        f"hiresquire.{func_name} is deprecated in v2. Use HireSquireClient instead: "
        f"client = HireSquireClient(); client.jobs.create(...)",
        DeprecationWarning,
        stacklevel=2,
    )


def create_screening_job(
    title: str,
    description: str,
    resumes: List[Union[str, Dict[str, str]]],
    leniency_level: int = 5,
    custom_instructions: str = "",
    webhook_url: str = "",
    idempotency_key: Optional[str] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Deprecated v1 wrapper. Use HireSquireClient.jobs.create() instead."""
    _v1_warning("create_screening_job")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.jobs.create(
        title,
        description,
        resumes,
        leniency_level=leniency_level,
        custom_instructions=custom_instructions,
        webhook_url=webhook_url or None,
        idempotency_key=idempotency_key,
    )


def get_screening_status(
    job_id: int,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("get_screening_status")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.jobs.get_status(job_id)


def get_screening_results(
    job_id: int,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("get_screening_results")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.jobs.get_results(job_id)


def wait_for_screening_completion(
    job_id: int,
    poll_interval: int = 3,
    max_wait_seconds: int = 300,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("wait_for_screening_completion")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.jobs.wait(job_id, poll_interval=poll_interval, max_wait_seconds=max_wait_seconds)


def generate_candidate_email(
    job_id: int,
    candidate_id: int,
    email_type: str = "invite",
    tone: str = "professional",
    custom_notes: str = "",
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("generate_candidate_email")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.emails.generate(job_id, candidate_id, email_type, tone, custom_notes)


def get_candidates_by_score(
    job_id: int,
    min_score: int = 0,
    max_score: int = 100,
    only_top_n: int = 0,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("get_candidates_by_score")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.jobs.get_results(
        job_id, min_score=min_score or None, only_top_n=only_top_n or None
    )


def cancel_screening_job(
    job_id: int,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("cancel_screening_job")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.jobs.cancel(job_id)


def report_hiring_outcome(
    job_id: int,
    candidate_id: int,
    outcome: str,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("report_hiring_outcome")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.jobs.report_outcome(job_id, candidate_id, outcome)


def test_webhook(
    url: str,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("test_webhook")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.utils.test_webhook(url)


def get_rate_limit(
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("get_rate_limit")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.utils.get_rate_limit()


def get_candidate(
    candidate_id: int,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("get_candidate")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.candidates.get(candidate_id)


def update_candidate_status(
    candidate_id: int,
    status: str,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("update_candidate_status")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.candidates.update_status(candidate_id, status)


def enable_auto_reload(
    threshold: float,
    amount: float,
    payment_method_id: str,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("enable_auto_reload")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.credits.enable_auto_reload(threshold, amount, payment_method_id)


def disable_auto_reload(
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("disable_auto_reload")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.credits.disable_auto_reload()


def purchase_credits(
    amount: Optional[float] = None,
    pack: Optional[str] = None,
    payment_method_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("purchase_credits")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.credits.purchase(
        amount=amount,
        pack=pack,
        payment_method_id=payment_method_id or "",
        idempotency_key=idempotency_key,
    )


def create_payment_intent(
    amount: float,
    payment_method_id: Optional[str] = None,
    return_url: Optional[str] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("create_payment_intent")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.credits.create_payment_intent(
        amount=amount,
        payment_method_id=payment_method_id,
        return_url=return_url,
    )


def list_credit_packs(
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("list_credit_packs")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.credits.list_packs()


def get_credit_transactions(
    limit: int = 50,
    offset: int = 0,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("get_credit_transactions")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.credits.get_transactions(limit=limit, offset=offset)


def list_calendar_connections(
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("list_calendar_connections")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.calendar.list()


def get_available_slots(
    provider: str,
    date: str,
    duration: int = 60,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("get_available_slots")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.calendar.get_slots(provider, date, duration)


def create_interview(
    job_id: int,
    candidate_id: int,
    scheduled_at: str,
    duration_minutes: int = 60,
    provider: Optional[str] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("create_interview")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.calendar.create_interview(
        job_id, candidate_id, scheduled_at, duration_minutes, provider
    )


def generate_meeting_link(
    provider: str,
    topic: str,
    duration: int = 60,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("generate_meeting_link")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.calendar.generate_meeting_link(provider, topic, duration)


def create_calendar_connection(
    provider: str,
    api_key: str,
    calendar_id: Optional[str] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("create_calendar_connection")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.calendar.connect(provider, api_key, calendar_id)


def whoami(
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("whoami")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.utils.whoami()


def list_agent_keys(
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("list_agent_keys")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.agent_keys.list()


def create_agent_key(
    name: str,
    monthly_spend_limit: Optional[float] = None,
    daily_spend_limit: Optional[float] = None,
    lifetime_spend_limit: Optional[float] = None,
    permissions: Optional[List[str]] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("create_agent_key")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.agent_keys.create(
        name, monthly_spend_limit, daily_spend_limit, lifetime_spend_limit, permissions
    )


def get_agent_key(
    key_id: int,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("get_agent_key")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.agent_keys.get(key_id)


def update_agent_key(
    key_id: int,
    name: Optional[str] = None,
    monthly_spend_limit: Optional[float] = None,
    daily_spend_limit: Optional[float] = None,
    lifetime_spend_limit: Optional[float] = None,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("update_agent_key")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.agent_keys.update(
        key_id,
        name=name,
        monthly_spend_limit=monthly_spend_limit,
        daily_spend_limit=daily_spend_limit,
        lifetime_spend_limit=lifetime_spend_limit,
    )


def revoke_agent_key(
    key_id: int,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("revoke_agent_key")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.agent_keys.revoke(key_id)


def regenerate_agent_key(
    key_id: int,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("regenerate_agent_key")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.agent_keys.regenerate(key_id)


def get_agent_key_usage(
    key_id: int,
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    _v1_warning("get_agent_key_usage")
    client = HireSquireClient(api_token=api_token, base_url=base_url)
    return client.agent_keys.get_usage(key_id)


def compare_candidates(
    candidates: List[Dict[str, Any]],
    candidate_ids: List[int],
) -> Dict[str, Any]:
    """Deprecated v1 wrapper. Local comparison; use client.jobs.compare() for server-side."""
    _v1_warning("compare_candidates")
    selected = [c for c in candidates if c.get("id") in candidate_ids]
    if len(selected) < 2:
        raise ValueError("Need at least 2 candidates to compare")
    sorted_candidates = sorted(selected, key=lambda x: x.get("score", 0), reverse=True)
    score_diff = sorted_candidates[0].get("score", 0) - sorted_candidates[-1].get("score", 0)
    return {
        "compared_count": len(selected),
        "top_candidate": sorted_candidates[0].get("name"),
        "top_score": sorted_candidates[0].get("score"),
        "score_range": score_diff,
        "candidates": [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "score": c.get("score"),
                "summary": c.get("summary", "")[:100],
            }
            for c in sorted_candidates
        ],
    }


def get_hiresquire_tools() -> List[Any]:
    """Deprecated v1 wrapper returning LangChain-compatible tool functions.

    Wraps tools with LangChain's ``@tool`` decorator when ``langchain_core`` or
    ``langchain`` is installed, and returns plain callables otherwise.
    """
    _v1_warning("get_hiresquire_tools")
    funcs: List[Any] = [
        create_screening_job,
        get_screening_status,
        get_screening_results,
        wait_for_screening_completion,
        generate_candidate_email,
        get_candidates_by_score,
        read_resume_from_file,
        compare_candidates,
        cancel_screening_job,
        report_hiring_outcome,
        test_webhook,
        get_rate_limit,
        get_candidate,
        update_candidate_status,
        enable_auto_reload,
        disable_auto_reload,
        purchase_credits,
        create_payment_intent,
        list_credit_packs,
        get_credit_transactions,
        list_calendar_connections,
        create_calendar_connection,
        get_available_slots,
        create_interview,
        generate_meeting_link,
        whoami,
        list_agent_keys,
        create_agent_key,
        get_agent_key,
        update_agent_key,
        revoke_agent_key,
        regenerate_agent_key,
        get_agent_key_usage,
    ]
    try:
        from langchain_core.tools import tool as lc_tool  # type: ignore[import-not-found]

        return [lc_tool(fn) for fn in funcs]
    except ImportError:
        try:
            from langchain.tools import tool as lc_tool_legacy  # type: ignore[import-not-found]

            return [lc_tool_legacy(fn) for fn in funcs]
        except ImportError:
            return funcs


__all__ = [
    "Config",
    "HireSquire",
    "HireSquireClient",
    "HireSquireError",
    "HttpClient",
    "__version__",
    "cancel_screening_job",
    "compare_candidates",
    "create_agent_key",
    "create_calendar_connection",
    "create_interview",
    "create_payment_intent",
    "create_screening_job",
    "disable_auto_reload",
    "enable_auto_reload",
    "generate_candidate_email",
    "generate_idempotency_key",
    "generate_meeting_link",
    "get_agent_key",
    "get_agent_key_usage",
    "get_available_slots",
    "get_candidate",
    "get_candidates_by_score",
    "get_credit_transactions",
    "get_hiresquire_tools",
    "get_rate_limit",
    "get_screening_results",
    "get_screening_status",
    "list_agent_keys",
    "list_calendar_connections",
    "list_credit_packs",
    "purchase_credits",
    "read_resume_from_file",
    "read_resumes_from_paths",
    "regenerate_agent_key",
    "report_hiring_outcome",
    "revoke_agent_key",
    "test_webhook",
    "update_agent_key",
    "update_candidate_status",
    "wait_for_screening_completion",
    "whoami",
]
