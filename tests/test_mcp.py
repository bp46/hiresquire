"""Tests for MCP server tool registration and basic behavior."""

from hiresquire.mcp_server import mcp


def test_mcp_tools_registered():
    tools = list(mcp._tool_manager._tools.keys())
    expected = {
        "create_screening",
        "get_screening_status",
        "get_results",
        "cancel_screening_job",
        "compare_candidates",
        "report_hiring_outcome",
        "generate_email",
        "bulk_generate_emails",
        "get_credit_balance",
        "estimate_screening_cost",
        "list_credit_packs",
        "get_credit_transactions",
        "purchase_credits",
        "create_checkout_session",
        "enable_auto_reload",
        "disable_auto_reload",
        "list_calendar_connections",
        "create_calendar_connection",
        "get_available_slots",
        "create_interview",
        "generate_meeting_link",
        "whoami",
        "get_rate_limit",
        "test_webhook",
        "get_api_schema",
        "audit_screening_job",
    }
    assert expected.issubset(set(tools)), f"missing: {expected - set(tools)}"


def test_create_screening_rejects_empty(monkeypatch):
    monkeypatch.setenv("HIRESQUIRE_API_TOKEN", "sk_test")
    fn = mcp._tool_manager._tools["create_screening"].fn
    result = fn(title="T", description="D" * 50)
    assert "error" in result


def test_mcp_missing_token_returns_error_dict(monkeypatch):
    import hiresquire.mcp_server as ms

    ms._client = None
    monkeypatch.delenv("HIRESQUIRE_API_TOKEN", raising=False)
    monkeypatch.setattr(
        "hiresquire.config.CONFIG_FILE",
        ms.Path("/nonexistent/config.json")
        if hasattr(ms, "Path")
        else __import__("pathlib").Path("/nonexistent/config.json"),
    )
    fn = mcp._tool_manager._tools["whoami"].fn
    result = fn()
    assert result["error"] == "AUTHENTICATION_ERROR"


def test_mcp_validation_error_returns_error_dict(monkeypatch):
    monkeypatch.setenv("HIRESQUIRE_API_TOKEN", "sk_test")
    fn = mcp._tool_manager._tools["create_screening"].fn
    result = fn(title="T", description="short", resumes=[{"filename": "a.txt", "content": "x"}])
    assert result["error"] == "VALIDATION_ERROR"
