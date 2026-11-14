"""Tests for the shared HTTP client using respx mocking."""

import httpx
import respx

from hiresquire.config import Config
from hiresquire.errors import (
    AuthenticationError,
    NotFoundError,
    PaymentRequiredError,
    ValidationError,
)
from hiresquire.http import HttpClient


@respx.mock
def test_http_get_success():
    route = respx.get("https://hiresquireai.com/api/v1/jobs/1").mock(
        return_value=httpx.Response(200, json={"job_id": 1, "status": "completed", "progress": 100})
    )
    client = HttpClient(api_token="sk_test")
    resp = client.get("jobs/1")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert route.called


@respx.mock
def test_http_auth_header():
    respx.get("https://hiresquireai.com/api/v1/jobs/1").mock(
        return_value=httpx.Response(200, json={"job_id": 1, "status": "completed"})
    )
    client = HttpClient(api_token="sk_test")
    client.get("jobs/1")
    req = respx.calls.last.request
    assert req.headers["authorization"] == "Bearer sk_test"
    assert req.headers["user-agent"].startswith("HireSquirePython/")


@respx.mock
def test_http_401_raises():
    respx.get("https://hiresquireai.com/api/v1/jobs/1").mock(
        return_value=httpx.Response(401, json={"error": "Unauthenticated", "message": "bad token"})
    )
    client = HttpClient(api_token="sk_bad")
    try:
        client.get("jobs/1")
        raise AssertionError("should have raised")
    except AuthenticationError as exc:
        assert exc.status_code == 401


@respx.mock
def test_http_429_retry():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"retry-after": "0"}, json={"error": "rate limited"})
        return httpx.Response(200, json={"job_id": 1, "status": "completed"})

    respx.get("https://hiresquireai.com/api/v1/jobs/1").mock(side_effect=handler)
    client = HttpClient(api_token="sk_test")
    resp = client.get("jobs/1")
    assert resp.status_code == 200
    assert len(calls) == 2


@respx.mock
def test_http_error_mapping():
    client = HttpClient(api_token="sk_test")
    for status, exc_cls in [
        (402, PaymentRequiredError),
        (404, NotFoundError),
        (422, ValidationError),
    ]:
        respx.get("https://hiresquireai.com/api/v1/jobs/999").mock(
            return_value=httpx.Response(status, json={"message": f"err {status}"})
        )
        try:
            client.get("jobs/999")
            raise AssertionError(f"expected {exc_cls.__name__}")
        except exc_cls as exc:
            assert exc.status_code == status


def test_config_env_precedence_and_permissions(tmp_path, monkeypatch):
    import stat

    cfg_path = tmp_path / "config.json"
    cfg = Config(api_token="sk_file", base_url="https://file.example.com/v1")
    cfg.save(str(cfg_path))
    mode = stat.S_IMODE(cfg_path.stat().st_mode)
    assert mode == 0o600

    monkeypatch.setenv("HIRESQUIRE_BASE_URL", "https://env.example.com/v1")
    loaded = Config.load(str(cfg_path))
    assert loaded.base_url == "https://env.example.com/v1"
    assert loaded.api_token == "sk_file"
