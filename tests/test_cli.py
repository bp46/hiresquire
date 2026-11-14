"""Tests for the CLI using typer.testing.CliRunner."""

from typer.testing import CliRunner

from hiresquire.cli import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "hiresquire" in result.output


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "2.0.0" in result.output


def test_init_no_token(monkeypatch):
    monkeypatch.delenv("HIRESQUIRE_API_TOKEN", raising=False)
    result = runner.invoke(app, ["init", "--token", "sk_x", "--yes"])
    assert result.exit_code == 0


def test_whoami_requires_token(monkeypatch):
    monkeypatch.delenv("HIRESQUIRE_API_TOKEN", raising=False)
    result = runner.invoke(app, ["whoami"])
    assert result.exit_code != 0


def test_new_cli_commands_help():
    for args in [
        ["agent-keys", "--help"],
        ["summary", "--help"],
        ["calendar:list", "--help"],
    ]:
        result = runner.invoke(app, args)
        assert result.exit_code == 0
