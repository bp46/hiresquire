"""Tests for HireSquireClient namespaces using respx mocking."""

import httpx
import respx

from hiresquire import HireSquireClient


@respx.mock
def test_jobs_create_and_wait():
    respx.post("https://hiresquireai.com/api/v1/jobs").mock(
        return_value=httpx.Response(
            202, json={"job_id": 42, "status": "processing", "status_url": "/jobs/42"}
        )
    )
    respx.get("https://hiresquireai.com/api/v1/jobs/42").mock(
        return_value=httpx.Response(
            200, json={"job_id": 42, "status": "completed", "progress": 100}
        )
    )
    respx.get("https://hiresquireai.com/api/v1/jobs/42/results").mock(
        return_value=httpx.Response(
            200,
            json={
                "job_id": 42,
                "job_title": "Job",
                "status": "completed",
                "total_candidates": 1,
                "candidates": [{"id": 1, "name": "Ada", "score": 92, "summary": "great"}],
            },
        )
    )
    client = HireSquireClient(api_token="sk_test")
    job = client.jobs.create("Title", "D" * 50, [{"filename": "a.pdf", "content": "c"}])
    assert job["job_id"] == 42
    status = client.jobs.get_status(42)
    assert status["status"] == "completed"
    results = client.jobs.get_results(42)
    assert results["candidates"][0]["name"] == "Ada"


@respx.mock
def test_credits_balance():
    respx.get("https://hiresquireai.com/api/v1/credits/balance").mock(
        return_value=httpx.Response(
            200,
            json={
                "balance": 10.0,
                "formatted_balance": "$10.00",
                "total_purchased": 10.0,
                "total_spent": 0.0,
                "cost_per_candidate": 0.01,
                "auto_reload_enabled": False,
            },
        )
    )
    client = HireSquireClient(api_token="sk_test")
    bal = client.credits.get_balance()
    assert bal["balance"] == 10.0


@respx.mock
def test_whoami():
    respx.get("https://hiresquireai.com/api/v1/schema/validate").mock(
        return_value=httpx.Response(
            200,
            json={
                "valid": True,
                "user": {"id": 1, "name": "Ada", "email": "ada@example.com"},
                "credits": {
                    "balance": 5.0,
                    "formatted_balance": "$5.00",
                    "total_purchased": 5.0,
                    "total_spent": 0.0,
                    "cost_per_candidate": 0.01,
                    "auto_reload_enabled": False,
                },
            },
        )
    )
    client = HireSquireClient(api_token="sk_test")
    info = client.utils.whoami()
    assert info["valid"] is True
    assert info["user"]["name"] == "Ada"


@respx.mock
def test_client_alias():
    from hiresquire import HireSquire

    client = HireSquire(api_token="sk_test")
    assert client.api_token == "sk_test"


@respx.mock
def test_v1_create_screening_job_wrapper(monkeypatch):
    monkeypatch.setenv("HIRESQUIRE_API_TOKEN", "sk_test")
    from hiresquire import create_screening_job

    respx.post("https://hiresquireai.com/api/v1/jobs").mock(
        return_value=httpx.Response(202, json={"job_id": 7, "status": "processing"})
    )
    result = create_screening_job("T", "D" * 50, [{"filename": "a.pdf", "content": "c"}])
    assert result["job_id"] == 7
    assert "idempotency-key" in respx.calls.last.request.headers


@respx.mock
def test_purchase_sends_idempotency_key():
    respx.post("https://hiresquireai.com/api/v1/credits/purchase").mock(
        return_value=httpx.Response(200, json={"success": True, "balance": 25.0})
    )
    client = HireSquireClient(api_token="sk_test")
    res = client.credits.purchase(pack="pouch", payment_method_id="pm_123")
    assert res["balance"] == 25.0
    assert "idempotency-key" in respx.calls.last.request.headers


@respx.mock
def test_v1_client_methods_and_pii_redaction():
    from hiresquire import HireSquire

    respx.get("https://hiresquireai.com/api/v1/schema/validate").mock(
        return_value=httpx.Response(
            200,
            json={
                "valid": True,
                "user": {"id": 1, "name": "Ada"},
                "credits": {"balance": 5.0, "formatted_balance": "$5.00"},
            },
        )
    )
    client = HireSquire(api_token="sk_test")
    assert client.whoami()["valid"] is True

    try:
        client.jobs._prepare_resumes([{"content": "secret@pii.example.com 555-1234"}])
        raise AssertionError("should have raised")
    except ValueError as exc:
        assert "secret@pii.example.com" not in str(exc)


def test_resume_min_length(tmp_path):
    from hiresquire.resume import ResumeParseError, read_resume_from_file

    short_file = tmp_path / "short.txt"
    short_file.write_text("too short", encoding="utf-8")
    try:
        read_resume_from_file(str(short_file))
        raise AssertionError("should have raised")
    except ResumeParseError:
        pass
