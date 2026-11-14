"""Tests for Pydantic models (single source of truth)."""

from hiresquire.models import (
    Candidate,
    CompareResponse,
    CreateJobRequest,
    CreditBalance,
    EmailResponse,
    RateLimitResponse,
    ResultsResponse,
    ResumeInput,
    SchemaResponse,
    WhoamiResponse,
)


def test_create_job_request_defaults():
    req = CreateJobRequest(
        title="Senior Developer",
        description="A" * 50,
        resumes=[ResumeInput(filename="a.pdf", content="content")],
    )
    assert req.leniency_level == 5
    assert req.title == "Senior Developer"


def test_create_job_request_validation():
    try:
        CreateJobRequest(
            title="",
            description="short",
            resumes=[],
        )
        raise AssertionError("should have raised")
    except Exception:
        pass


def test_candidate_model():
    c = Candidate(id=1, name="Ada", score=92, summary="Great fit")
    assert c.score == 92
    assert c.strengths == []


def test_results_response():
    r = ResultsResponse(
        job_id=1,
        job_title="Job",
        status="completed",
        total_candidates=2,
        candidates=[Candidate(id=1, name="A", score=90, summary="s")],
    )
    assert r.total_candidates == 2


def test_credit_balance():
    b = CreditBalance(
        balance=25.5,
        formatted_balance="$25.50",
        total_purchased=30.0,
        total_spent=4.5,
        cost_per_candidate=0.01,
        auto_reload_enabled=False,
    )
    assert b.formatted_balance == "$25.50"


def test_backend_response_shapes():
    res = ResultsResponse.model_validate(
        {
            "job_id": 1,
            "title": "Senior Python Dev",
            "status": "completed",
            "total_candidates": 1,
            "candidates": [{"id": 1, "name": "Ada", "score": 95, "summary": None}],
        }
    )
    assert res.job_title == "Senior Python Dev"
    assert res.title == "Senior Python Dev"

    who = WhoamiResponse.model_validate(
        {
            "valid": True,
            "user": {"id": 1, "name": "Ada", "email": "ada@example.com"},
            "credits": {
                "balance": 12.5,
                "formatted_balance": "$12.50",
                "is_low": False,
                "auto_reload_enabled": False,
            },
        }
    )
    assert who.credits.balance == 12.5

    em = EmailResponse.model_validate(
        {
            "success": True,
            "candidate_id": 5,
            "candidate_name": "Ada",
            "email": {"subject": "Interview Invite", "body": "Hello Ada"},
        }
    )
    assert em.subject == "Interview Invite"
    assert em.body == "Hello Ada"

    cmp = CompareResponse.model_validate(
        {
            "job_id": 1,
            "compared_count": 2,
            "top_candidate": "Ada",
            "top_score": 95,
            "score_range": 15,
            "candidates": [{"id": 1, "name": "Ada", "score": 95, "summary": "Great"}],
            "delta_analysis": {"summary": "Ada leads"},
        }
    )
    assert cmp.top_candidate == "Ada"

    rl = RateLimitResponse.model_validate(
        {"limit": 60, "remaining": 60, "reset_at": None, "reset_in_seconds": 0}
    )
    assert rl.reset_at is None

    sc = SchemaResponse.model_validate({"version": "1.0", "candidate_fields": []})
    assert sc.endpoints == []
