"""HireSquire CLI — Typer-based command line interface.

Single `hiresquire` command exposing the full SDK surface with --json support
and rich human-readable output.
"""

import json
import time
from typing import Dict, List, NoReturn, Optional, Union, cast

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .client import HireSquireClient
from .config import CONFIG_FILE, Config
from .errors import HireSquireError
from .resume import read_resume_from_file, read_resumes_from_paths

app = typer.Typer(
    name="hiresquire",
    help="HireSquire AI-powered candidate screening — SDK, CLI, and MCP server.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"hiresquire {__version__}")
        raise typer.Exit()


_JSON_OUTPUT = [False]


@app.callback()
def _global(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version",
        callback=_version_callback,
        is_eager=True,
    ),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    _JSON_OUTPUT[0] = json


def _json(data: dict) -> None:
    if _JSON_OUTPUT[0]:
        typer.echo(json.dumps(data, indent=2, default=str))
        raise typer.Exit(code=0)


def _handle_error(error: Exception, context: str = "Operation failed") -> NoReturn:
    if isinstance(error, HireSquireError):
        msg = f"[{error.code}] {error.message}" if error.code else error.message
    else:
        msg = str(error)
    if _JSON_OUTPUT[0]:
        typer.echo(json.dumps({"success": False, "error": msg, "context": context}, indent=2))
        raise typer.Exit(code=1)
    console.print(f"[red]Error:[/red] {msg}")
    raise typer.Exit(code=1)


def _client() -> HireSquireClient:
    try:
        return HireSquireClient()
    except Exception as exc:
        _handle_error(exc, "Authentication")


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@app.command()
def init(
    token: Optional[str] = typer.Option(None, "--token", "-t", help="API token"),
    base_url: Optional[str] = typer.Option(None, "--base-url", "-u", help="API base URL"),
    webhook: Optional[str] = typer.Option(None, "--webhook", "-w", help="Default webhook URL"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Initialize configuration with API token."""
    config = Config.load()
    if token:
        config.api_token = token
    if base_url:
        config.base_url = base_url
    if webhook:
        config.webhook_url = webhook

    if not config.api_token:
        _handle_error(
            ValueError("API token is required. Use --token or set HIRESQUIRE_API_TOKEN."),
            "init",
        )

    if not yes and not _JSON_OUTPUT[0]:
        confirm = typer.confirm(f"Save config to {CONFIG_FILE}?")
        if not confirm:
            console.print("[yellow]Configuration cancelled.[/yellow]")
            raise typer.Exit(code=0)

    config.save()
    result = {
        "success": True,
        "message": "Configuration saved",
        "config_path": str(CONFIG_FILE),
    }
    _json(result)
    console.print("[green]✓[/green] Configuration saved successfully")
    console.print(f"  [dim]Config: {CONFIG_FILE}[/dim]")


# ---------------------------------------------------------------------------
# screen
# ---------------------------------------------------------------------------


@app.command()
def screen(
    title: str = typer.Option(..., "--title", "-t", help="Job posting title"),
    description: str = typer.Option(..., "--description", "-d", help="Job description (or @file)"),
    resumes: Optional[str] = typer.Option(
        None, "--resumes", "-r", help="Resume files/dirs (comma-separated or @file)"
    ),
    zip_path: Optional[str] = typer.Option(None, "--zip", "-z", help="ZIP file of resumes"),
    leniency: int = typer.Option(5, "--leniency", "-l", min=1, max=10, help="Leniency 1-10"),
    webhook: Optional[str] = typer.Option(None, "--webhook", "-w", help="Webhook URL"),
    watch: bool = typer.Option(False, "--watch", help="Poll for completion"),
    poll_timeout: int = typer.Option(300, "--poll-timeout", help="Max poll seconds"),
    min_score: Optional[int] = typer.Option(None, "--min-score", help="Min score threshold"),
    only_top_n: Optional[int] = typer.Option(None, "--only-top-n", help="Top N candidates"),
) -> None:
    """Submit a candidate screening job."""
    client = _client()
    config = Config.load()

    job_description = description
    if description.startswith("@"):
        path = description[1:]
        try:
            parsed = read_resume_from_file(path)
            job_description = parsed["content"]
        except Exception as exc:
            _handle_error(exc, "Reading description file")

    webhook_url = webhook or config.webhook_url

    try:
        if zip_path:
            result = client.jobs.create_from_zip(
                title,
                job_description,
                zip_path,
                leniency_level=leniency,
                webhook_url=webhook_url,
            )
            if _JSON_OUTPUT[0] and not watch:
                _json(
                    {
                        "success": True,
                        "job_id": result["job_id"],
                        "status": result["status"],
                        "status_url": result.get("status_url"),
                    }
                )
                return
            console.print(f"[blue]Job #{result['job_id']} created from ZIP[/blue]")
        else:
            if not resumes:
                _handle_error(ValueError("Provide --resumes or --zip"), "screen")
            paths = resumes.split(",")
            if resumes.startswith("@"):
                with open(resumes[1:], "r") as f:
                    paths = [l.strip() for l in f if l.strip()]
            resume_objects: List[Dict[str, str]] = read_resumes_from_paths(paths)
            if not resume_objects:
                _handle_error(ValueError("No resume files found"), "screen")
            result = client.jobs.create(
                title,
                job_description,
                cast(List[Union[str, Dict[str, str]]], resume_objects),
                leniency_level=leniency,
                webhook_url=webhook_url,
            )
            if _JSON_OUTPUT[0] and not watch:
                _json(
                    {
                        "success": True,
                        "job_id": result["job_id"],
                        "status": result["status"],
                        "status_url": result.get("status_url"),
                    }
                )
                return
            console.print(f"[blue]Job #{result['job_id']} created[/blue]")
            console.print(f"  [dim]Poll: {result.get('status_url')}[/dim]")

        if watch:
            start = time.time()
            status = {}
            while time.time() - start < poll_timeout:
                status = client.jobs.get_status(result["job_id"])
                if status["status"] in ("completed", "failed"):
                    break
                time.sleep(3)
            if status.get("status") == "completed":
                results = client.jobs.get_results(
                    result["job_id"], min_score=min_score, only_top_n=only_top_n
                )
                if _JSON_OUTPUT[0]:
                    _json(
                        {
                            "type": "job_completed",
                            "success": True,
                            "job_id": result["job_id"],
                            "results": results,
                        }
                    )
                    return
                console.print(
                    f"\n[green]✓ Screening complete![/green] {len(results['candidates'])} candidates"
                )
                _print_results_table(results)
            else:
                _handle_error(
                    HireSquireError(f"Job {result['job_id']} failed or timed out"), "screen"
                )
    except Exception as exc:
        _handle_error(exc, "screen")


def _print_results_table(results: dict) -> None:
    table = Table(title=f"Results: {results.get('job_title')}")
    table.add_column("#", style="bold", width=4)
    table.add_column("Candidate")
    table.add_column("Score", justify="right", width=8)
    table.add_column("Summary")
    for i, c in enumerate(results["candidates"], 1):
        score = c["score"]
        color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
        table.add_row(
            str(i),
            c["name"],
            f"[{color}]{score}/100[/{color}]",
            (c.get("summary") or "")[:80],
        )
    console.print(table)


# ---------------------------------------------------------------------------
# jobs
# ---------------------------------------------------------------------------


@app.command()
def jobs(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    page: int = typer.Option(1, "--page", "-p"),
    limit: int = typer.Option(10, "--limit", "-l"),
) -> None:
    """List all screening jobs."""
    client = _client()
    try:
        data = client.jobs.list(status=status, page=page, per_page=limit)
        items = data.get("jobs", data.get("data", []))
        if _JSON_OUTPUT[0]:
            _json(
                {
                    "success": True,
                    "jobs": items,
                    "total": data.get("total", len(items)),
                    "page": page,
                }
            )
            return
        if not items:
            console.print("[yellow]No jobs found.[/yellow]")
            return
        console.print(f"[blue]Jobs ({data.get('total', len(items))} total):[/blue]")
        for j in items:
            console.print(f"  [bold]#{j.get('id') or j.get('job_id')}[/bold] {j.get('title')}")
            console.print(
                f"     Status: {j.get('status')} | "
                f"Candidates: {j.get('total_candidates', j.get('candidate_count', 0))}"
            )
    except HireSquireError as exc:
        _handle_error(exc, "jobs")


# ---------------------------------------------------------------------------
# results
# ---------------------------------------------------------------------------


@app.command()
def results(
    job: int = typer.Option(..., "--job", "-j", help="Job ID"),
    min_score: Optional[int] = typer.Option(None, "--min-score"),
    only_top_n: Optional[int] = typer.Option(None, "--only-top-n"),
) -> None:
    """Get results for a screening job."""
    client = _client()
    try:
        data = client.jobs.get_results(job, min_score=min_score, only_top_n=only_top_n)
        if _JSON_OUTPUT[0]:
            _json({"success": True, "job_id": data["job_id"], "results": data})
            return
        console.print(f"[blue]Results for: {data.get('job_title')}[/blue]\n")
        _print_results_table(data)
    except HireSquireError as exc:
        _handle_error(exc, "results")


@app.command()
def summary(
    job: int = typer.Option(..., "--job", "-j", help="Job ID"),
) -> None:
    """Show AI summary and top candidates for a completed screening job."""
    client = _client()
    try:
        data = client.jobs.get_results(job)
        if _JSON_OUTPUT[0]:
            _json(
                {
                    "success": True,
                    "job_id": data["job_id"],
                    "job_title": data.get("job_title") or data.get("title"),
                    "total_candidates": data.get("total_candidates", 0),
                    "agent_summary": data.get("agent_summary"),
                }
            )
            return
        console.print(f"[blue]Summary for: {data.get('job_title') or data.get('title')}[/blue]")
        console.print(f"  Total candidates: {data.get('total_candidates', 0)}")
        if data.get("agent_summary"):
            console.print(f"\n{data['agent_summary']}")
    except Exception as exc:
        _handle_error(exc, "summary")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@app.command()
def status(
    job: int = typer.Option(..., "--job", "-j", help="Job ID"),
    watch: bool = typer.Option(False, "--watch", "-w"),
    poll_timeout: int = typer.Option(300, "--poll-timeout"),
) -> None:
    """Check the status of a screening job."""
    client = _client()
    try:
        if watch:
            start = time.time()
            st: Dict[str, object] = {}
            while time.time() - start < poll_timeout:
                st = client.jobs.get_status(job)
                if not _JSON_OUTPUT[0]:
                    console.print(f"\r  Status: [bold]{st['status']}[/bold]", end="")
                if st["status"] in ("completed", "failed"):
                    if not _JSON_OUTPUT[0]:
                        console.print()
                    break
                time.sleep(3)
            if st.get("status") not in ("completed",):
                _handle_error(
                    HireSquireError(f"Job {job} did not complete (status: {st.get('status')})"),
                    "status",
                )
            if _JSON_OUTPUT[0]:
                _json({"success": True, "job_id": job, "status": st["status"]})
                return
            console.print(f"[green]✓[/green] Job #{job} completed")
            return
        st = client.jobs.get_status(job)
        if _JSON_OUTPUT[0]:
            _json(
                {
                    "success": True,
                    "job_id": st["job_id"],
                    "status": st["status"],
                    "progress": st.get("progress"),
                }
            )
            return
        console.print(f"[blue]Job #{job}[/blue]")
        console.print(f"  Status: {st['status']}")
        if st.get("progress") is not None:
            console.print(f"  Progress: {st['progress']}%")
    except HireSquireError as exc:
        _handle_error(exc, "status")


# ---------------------------------------------------------------------------
# email
# ---------------------------------------------------------------------------


@app.command()
def email(
    job: int = typer.Option(..., "--job", "-j"),
    candidate: int = typer.Option(..., "--candidate", "-c"),
    type: str = typer.Option(
        "invite", "--type", "-t", help="invite, rejection, keep-warm, followup"
    ),
    tone: str = typer.Option("professional", "--tone", "-T", help="professional, friendly, formal"),
    message: Optional[str] = typer.Option(None, "--message", "-m"),
) -> None:
    """Generate an email for a candidate."""
    client = _client()
    try:
        data = client.emails.generate(job, candidate, type, tone, message or "")
        if _JSON_OUTPUT[0]:
            _json(
                {
                    "success": True,
                    "candidate_id": data["candidate_id"],
                    "email_type": data["email_type"],
                    "subject": data["subject"],
                    "body": data["body"],
                }
            )
            return
        console.print(
            f"[blue]Email Generated[/blue]\n  Type: {data['email_type']}\n  "
            f"Subject: {data['subject']}\n"
        )
        console.print(data["body"])
    except HireSquireError as exc:
        _handle_error(exc, "email")


# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------


@app.command()
def configure(
    token: Optional[str] = typer.Option(None, "--token", "-t"),
    base_url: Optional[str] = typer.Option(None, "--base-url", "-u"),
    webhook: Optional[str] = typer.Option(None, "--webhook", "-w"),
    leniency: Optional[int] = typer.Option(None, "--leniency", "-l"),
    clear: bool = typer.Option(False, "--clear"),
    yes: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    """Update configuration settings."""
    config = Config.load()
    if clear:
        if not yes and not _JSON_OUTPUT[0]:
            if not typer.confirm("Clear all configuration?"):
                console.print("[yellow]Configuration cancelled.[/yellow]")
                raise typer.Exit(code=0)
        config.clear()
        _json({"success": True, "message": "Configuration cleared"})
        console.print("[green]✓[/green] Configuration cleared")
        return

    updated = False
    if token:
        config.api_token = token
        updated = True
    if base_url:
        config.base_url = base_url
        updated = True
    if webhook:
        config.webhook_url = webhook
        updated = True
    if leniency:
        config.default_leniency = leniency
        updated = True

    if updated:
        config.save()

    if _JSON_OUTPUT[0]:
        _json(
            {
                "success": True,
                "config": {
                    "baseUrl": config.base_url,
                    "webhookUrl": config.webhook_url,
                    "defaultLeniency": config.default_leniency,
                },
            }
        )
        return
    console.print("[green]✓[/green] Configuration updated")
    console.print(f"  API URL: {config.base_url}")
    console.print(f"  Webhook: {config.webhook_url or '(not set)'}")
    console.print(f"  Default Leniency: {config.default_leniency}")


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


@app.command()
def cancel(
    job: int = typer.Option(..., "--job", "-j"),
) -> None:
    """Cancel a running screening job."""
    client = _client()
    try:
        result = client.jobs.cancel(job)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print(f"[green]✓[/green] Job #{job} cancelled")
        console.print(f"  Status: {result.get('status')}")
        console.print(f"  Message: {result.get('message')}")
    except HireSquireError as exc:
        _handle_error(exc, "cancel")


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------


@app.command()
def compare(
    job: int = typer.Option(..., "--job", "-j"),
    candidates: str = typer.Option(..., "--candidates", "-c", help="Comma-separated candidate IDs"),
) -> None:
    """Compare candidates side-by-side."""
    client = _client()
    try:
        ids = [int(x.strip()) for x in candidates.split(",")]
        result = client.jobs.compare(job, ids)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        comp = result.get("comparison") or {}
        top_candidate = result.get("top_candidate") or comp.get("top_candidate", "N/A")
        score_range = result.get("score_range")
        if score_range is None:
            score_range = comp.get("score_diff", comp.get("score_range", "N/A"))
        console.print(f"[blue]Comparison ({len(result['candidates'])} candidates)[/blue]\n")
        console.print(f"  [green]Top Candidate:[/green] {top_candidate}")
        console.print(f"  Score difference: {score_range}\n")
        for i, cand in enumerate(result["candidates"], 1):
            console.print(f"{i}. {cand['name']} ({cand['score']})")
    except Exception as exc:
        _handle_error(exc, "compare")


# ---------------------------------------------------------------------------
# outcome
# ---------------------------------------------------------------------------


@app.command()
def outcome(
    job: int = typer.Option(..., "--job", "-j"),
    candidate: int = typer.Option(..., "--candidate", "-c"),
    outcome: str = typer.Option(..., "--outcome", "-o", help="hired, rejected, withdrawn"),
) -> None:
    """Report hiring outcome."""
    valid = {"hired", "rejected", "withdrawn"}
    if outcome not in valid:
        _handle_error(ValueError(f"Invalid outcome. Must be: {', '.join(valid)}"), "outcome")
    client = _client()
    try:
        result = client.jobs.report_outcome(job, candidate, outcome)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print("[green]✓[/green] Outcome reported")
        console.print(f"  Message: {result.get('message')}")
    except HireSquireError as exc:
        _handle_error(exc, "outcome")


# ---------------------------------------------------------------------------
# whoami
# ---------------------------------------------------------------------------


@app.command(name="whoami")
def whoami_cmd() -> None:
    """Verify API token and get profile info."""
    client = _client()
    try:
        result = client.utils.whoami()
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        user = result.get("user", {})
        credits = result.get("credits", {})
        console.print("[blue]Agent Profile[/blue]")
        console.print(f"  Name: {user.get('name')}")
        console.print(f"  Email: {user.get('email')}")
        console.print(f"  Balance: {credits.get('formatted_balance', 'N/A')}")
        if credits.get("is_low"):
            console.print("[yellow]⚠[/yellow] Credit balance is low.")
    except HireSquireError as exc:
        _handle_error(exc, "whoami")


# ---------------------------------------------------------------------------
# rate-limit
# ---------------------------------------------------------------------------


@app.command(name="rate-limit")
def rate_limit() -> None:
    """Check current API rate limit status."""
    client = _client()
    try:
        result = client.utils.get_rate_limit()
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print("[blue]Rate Limit Status[/blue]")
        console.print(f"  Limit: {result.get('limit')} requests/minute")
        console.print(f"  Remaining: {result.get('remaining')}")
        console.print(f"  Resets: {result.get('reset_at')}")
    except HireSquireError as exc:
        _handle_error(exc, "rate-limit")


# ---------------------------------------------------------------------------
# candidate / set-status
# ---------------------------------------------------------------------------


@app.command()
def candidate(
    id: int = typer.Option(..., "--id", "-i"),
) -> None:
    """Get details of a specific candidate."""
    client = _client()
    try:
        result = client.candidates.get(id)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print(f"[blue]{result.get('name')}[/blue]")
        console.print(f"  Score: {result.get('score')}")
        console.print(f"  Email: {result.get('email', 'N/A')}")
        console.print(f"  Status: {result.get('status', 'N/A')}")
        console.print(f"  Summary: {(result.get('summary') or '')[:150]}")
    except HireSquireError as exc:
        _handle_error(exc, "candidate")


@app.command(name="set-status")
def set_status(
    id: int = typer.Option(..., "--id", "-i"),
    status: str = typer.Option(..., "--status", "-s"),
) -> None:
    """Update a candidate's status."""
    client = _client()
    try:
        result = client.candidates.update_status(id, status)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print(f"[green]✓[/green] Status updated to {status}")
    except Exception as exc:
        _handle_error(exc, "set-status")


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


@app.command("schema")
def schema_cmd() -> None:
    """Get API schema for discovery."""
    client = _client()
    try:
        result = client.utils.get_api_schema()
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print(f"[blue]API Schema v{result.get('version')}[/blue]\n")
        for ep in result.get("endpoints", []):
            console.print(f"  [bold]{ep.get('path')}[/bold]")
            console.print(f"    Methods: {', '.join(ep.get('methods', []))}")
            console.print(f"    {ep.get('description')}")
            console.print()
    except HireSquireError as exc:
        _handle_error(exc, "schema")


# ---------------------------------------------------------------------------
# webhook-test
# ---------------------------------------------------------------------------


@app.command(name="webhook-test")
def webhook_test(
    url: str = typer.Option(..., "--url", "-u"),
) -> None:
    """Test a webhook endpoint."""
    client = _client()
    try:
        result = client.utils.test_webhook(url)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        if result.get("success"):
            console.print("[green]✓[/green] Webhook test successful")
        else:
            console.print("[red]✗[/red] Webhook test failed")
        console.print(f"  Message: {result.get('message')}")
    except HireSquireError as exc:
        _handle_error(exc, "webhook-test")


# ---------------------------------------------------------------------------
# credits
# ---------------------------------------------------------------------------

credits_app = typer.Typer(help="Manage prepaid credits")
app.add_typer(credits_app, name="credits")


@credits_app.command("balance")
def credits_balance() -> None:
    client = _client()
    try:
        result = client.credits.get_balance()
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print("[blue]Credit Balance[/blue]")
        console.print(f"  Balance: [bold]{result.get('formatted_balance')}[/bold]")
        console.print(f"  Total Purchased: ${result.get('total_purchased')}")
        console.print(f"  Total Spent: ${result.get('total_spent')}")
        console.print(
            f"  Auto-reload: {'enabled' if result.get('auto_reload_enabled') else 'disabled'}"
        )
    except HireSquireError as exc:
        _handle_error(exc, "credits balance")


@credits_app.command("list-packs")
def credits_list_packs() -> None:
    client = _client()
    try:
        result = client.credits.list_packs()
        packs = result.get("packs", [])
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print("[blue]Credit Packs[/blue]")
        for p in packs:
            console.print(
                f"  [bold]{p.get('id')}[/bold]: ${p.get('price')} for {p.get('credits')} credits"
            )
    except HireSquireError as exc:
        _handle_error(exc, "credits list-packs")


@credits_app.command("checkout")
def credits_checkout(
    pack: Optional[str] = typer.Option(None, "--pack", "-p"),
    amount: Optional[float] = typer.Option(None, "--amount", "-a"),
) -> None:
    client = _client()
    try:
        result = client.credits.create_checkout_session(amount=amount, pack=pack)
        if _JSON_OUTPUT[0]:
            _json(
                {
                    "success": True,
                    "checkout_url": result.get("checkout_url"),
                    "amount": result.get("amount"),
                    "expires_at": result.get("expires_at"),
                }
            )
            return
        console.print("[blue]Checkout Session Created[/blue]")
        console.print(f"  Payment Link: {result.get('checkout_url')}")
    except HireSquireError as exc:
        _handle_error(exc, "credits checkout")


@credits_app.command("transactions")
def credits_transactions(
    limit: int = typer.Option(20, "--limit", "-l"),
) -> None:
    client = _client()
    try:
        result = client.credits.get_transactions(limit=limit)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print("[blue]Credit Transactions[/blue]")
        for tx in result.get("transactions", []):
            sign = "+" if tx.get("amount", 0) >= 0 else ""
            console.print(
                f"  {sign}${tx.get('amount')} - {tx.get('description', tx.get('type', ''))}"
            )
    except HireSquireError as exc:
        _handle_error(exc, "credits transactions")


@credits_app.command("auto-reload-enable")
def credits_auto_reload_enable(
    threshold: float = typer.Option(..., "--threshold"),
    amount: float = typer.Option(..., "--amount"),
    payment_method_id: str = typer.Option(..., "--payment-method-id"),
) -> None:
    client = _client()
    try:
        client.credits.enable_auto_reload(threshold, amount, payment_method_id)
        if _JSON_OUTPUT[0]:
            _json({"success": True, "message": "Auto-reload enabled"})
            return
        console.print("[green]✓[/green] Auto-reload enabled")
        console.print(f"  Threshold: ${threshold} | Amount: ${amount} per reload")
    except HireSquireError as exc:
        _handle_error(exc, "credits auto-reload-enable")


@credits_app.command("auto-reload-disable")
def credits_auto_reload_disable() -> None:
    client = _client()
    try:
        client.credits.disable_auto_reload()
        if _JSON_OUTPUT[0]:
            _json({"success": True, "message": "Auto-reload disabled"})
            return
        console.print("[green]✓[/green] Auto-reload disabled")
    except HireSquireError as exc:
        _handle_error(exc, "credits auto-reload-disable")


@credits_app.command("purchase")
def credits_purchase(
    pack: Optional[str] = typer.Option(None, "--pack", "-p"),
    amount: Optional[float] = typer.Option(None, "--amount", "-a"),
    payment_method_id: str = typer.Option(..., "--payment-method-id"),
) -> None:
    client = _client()
    try:
        result = client.credits.purchase(
            amount=amount, pack=pack, payment_method_id=payment_method_id
        )
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print("[green]✓[/green] Purchase successful")
        console.print(f"  New balance: {result.get('balance')}")
    except Exception as exc:
        _handle_error(exc, "credits purchase")


# ---------------------------------------------------------------------------
# agent-keys
# ---------------------------------------------------------------------------

agent_keys_app = typer.Typer(help="Manage autonomous agent API keys")
app.add_typer(agent_keys_app, name="agent-keys")


@agent_keys_app.command("list")
def agent_keys_list() -> None:
    """List agent API keys."""
    client = _client()
    try:
        result = client.agent_keys.list()
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        keys = result.get("keys", result.get("data", []))
        console.print(f"[blue]Agent Keys ({len(keys)})[/blue]")
        for k in keys:
            console.print(f"  [bold]#{k.get('id')}[/bold] {k.get('name')} ({k.get('key_prefix')})")
    except Exception as exc:
        _handle_error(exc, "agent-keys list")


@agent_keys_app.command("create")
def agent_keys_create(
    name: str = typer.Option(..., "--name", "-n"),
    monthly_limit: Optional[float] = typer.Option(None, "--monthly-limit"),
    daily_limit: Optional[float] = typer.Option(None, "--daily-limit"),
    lifetime_limit: Optional[float] = typer.Option(None, "--lifetime-limit"),
    permissions: Optional[str] = typer.Option(None, "--permissions", help="Comma-separated scopes"),
) -> None:
    """Create a new agent API key."""
    client = _client()
    try:
        perms = [p.strip() for p in permissions.split(",") if p.strip()] if permissions else None
        result = client.agent_keys.create(
            name=name,
            monthly_spend_limit=monthly_limit,
            daily_spend_limit=daily_limit,
            lifetime_spend_limit=lifetime_limit,
            permissions=perms,
        )
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print("[green]✓[/green] Agent key created")
        key_data = result.get("data", result)
        console.print(f"  ID: {key_data.get('id')} | Name: {key_data.get('name')}")
        if key_data.get("key"):
            console.print(f"  Key: {key_data['key']}")
    except Exception as exc:
        _handle_error(exc, "agent-keys create")


@agent_keys_app.command("get")
def agent_keys_get(
    id: int = typer.Option(..., "--id", "-i"),
) -> None:
    """Get details for an agent API key."""
    client = _client()
    try:
        result = client.agent_keys.get(id)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print(f"[blue]Agent Key #{id}[/blue]")
        console.print(f"  Name: {result.get('name')} | Active: {result.get('is_active')}")
    except Exception as exc:
        _handle_error(exc, "agent-keys get")


@agent_keys_app.command("update")
def agent_keys_update(
    id: int = typer.Option(..., "--id", "-i"),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
    monthly_limit: Optional[float] = typer.Option(None, "--monthly-limit"),
    daily_limit: Optional[float] = typer.Option(None, "--daily-limit"),
    lifetime_limit: Optional[float] = typer.Option(None, "--lifetime-limit"),
) -> None:
    """Update an agent API key."""
    client = _client()
    try:
        kwargs: Dict[str, object] = {}
        if name is not None:
            kwargs["name"] = name
        if monthly_limit is not None:
            kwargs["monthly_spend_limit"] = monthly_limit
        if daily_limit is not None:
            kwargs["daily_spend_limit"] = daily_limit
        if lifetime_limit is not None:
            kwargs["lifetime_spend_limit"] = lifetime_limit
        result = client.agent_keys.update(id, **kwargs)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print(f"[green]✓[/green] Agent key #{id} updated")
    except Exception as exc:
        _handle_error(exc, "agent-keys update")


@agent_keys_app.command("revoke")
def agent_keys_revoke(
    id: int = typer.Option(..., "--id", "-i"),
) -> None:
    """Revoke (delete) an agent API key."""
    client = _client()
    try:
        result = client.agent_keys.revoke(id)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print(f"[green]✓[/green] Agent key #{id} revoked")
    except Exception as exc:
        _handle_error(exc, "agent-keys revoke")


@agent_keys_app.command("regenerate")
def agent_keys_regenerate(
    id: int = typer.Option(..., "--id", "-i"),
) -> None:
    """Regenerate an agent API key."""
    client = _client()
    try:
        result = client.agent_keys.regenerate(id)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print(f"[green]✓[/green] Agent key #{id} regenerated")
    except Exception as exc:
        _handle_error(exc, "agent-keys regenerate")


@agent_keys_app.command("usage")
def agent_keys_usage(
    id: int = typer.Option(..., "--id", "-i"),
) -> None:
    """Get usage metrics for an agent API key."""
    client = _client()
    try:
        result = client.agent_keys.get_usage(id)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print(f"[blue]Usage for Agent Key #{id}[/blue]")
        console.print(f"  Total spent: ${result.get('total_spent', 0)}")
        console.print(f"  Month spent: ${result.get('month_spent', 0)}")
        console.print(f"  Day spent: ${result.get('day_spent', 0)}")
    except Exception as exc:
        _handle_error(exc, "agent-keys usage")


# ---------------------------------------------------------------------------
# calendar
# ---------------------------------------------------------------------------

calendar_app = typer.Typer(help="Manage calendar connections")
app.add_typer(calendar_app, name="calendar")


@calendar_app.command("connect")
def calendar_connect(
    provider: str = typer.Argument(..., help="calendly or calcom"),
    token: Optional[str] = typer.Option(None, "--token", "-t"),
    api_key: Optional[str] = typer.Option(None, "--api-key"),
    calendar_id: Optional[str] = typer.Option(None, "--calendar-id", "-c"),
) -> None:
    client = _client()
    key = token or api_key
    try:
        result = client.calendar.connect(provider, key or "", calendar_id)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print("[green]✓[/green] Calendar connection created")
        console.print(f"  Provider: {result.get('data', {}).get('provider', provider)}")
    except HireSquireError as exc:
        _handle_error(exc, "calendar connect")


@calendar_app.command("list")
def calendar_list() -> None:
    client = _client()
    try:
        result = client.calendar.list()
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print("[blue]Calendar Connections[/blue]")
        for conn in result.get("data", result if isinstance(result, list) else []):
            console.print(f"  [bold]{conn.get('provider')}[/bold] - {conn.get('status')}")
    except HireSquireError as exc:
        _handle_error(exc, "calendar list")


# ---------------------------------------------------------------------------
# interviews
# ---------------------------------------------------------------------------

interviews_app = typer.Typer(help="Schedule interviews")
app.add_typer(interviews_app, name="interviews")


@interviews_app.command("schedule")
def interviews_schedule(
    job: int = typer.Option(..., "--job", "-j"),
    candidate: int = typer.Option(..., "--candidate", "-c"),
    time: str = typer.Option(..., "--time", "-t", help="ISO 8601 datetime"),
    duration: int = typer.Option(60, "--duration", "-d"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p"),
) -> None:
    client = _client()
    try:
        result = client.calendar.create_interview(job, candidate, time, duration, provider)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print("[green]✓[/green] Interview scheduled")
        console.print(f"  Interview ID: {result.get('data', {}).get('id')}")
        if result.get("data", {}).get("meeting_link"):
            console.print(f"  Meeting Link: {result['data']['meeting_link']}")
    except HireSquireError as exc:
        _handle_error(exc, "interviews schedule")


@interviews_app.command("list")
def interviews_list(
    job: Optional[int] = typer.Option(None, "--job", "-j"),
) -> None:
    client = _client()
    try:
        resp = client.http.get("interviews", params={"job_id": job} if job else None)
        data = resp.json().get("data", [])
        if _JSON_OUTPUT[0]:
            _json(resp.json())
            return
        console.print("[blue]Interviews[/blue]")
        for iv in data:
            console.print(
                f"  ID: {iv.get('id')} | Job: {iv.get('job_posting_id')} | "
                f"Candidate: {iv.get('candidate_id')}"
            )
            console.print(f"    Scheduled: {iv.get('scheduled_at')} | Status: {iv.get('status')}")
    except HireSquireError as exc:
        _handle_error(exc, "interviews list")


# ---------------------------------------------------------------------------
# meetings
# ---------------------------------------------------------------------------

meetings_app = typer.Typer(help="Generate meeting links")
app.add_typer(meetings_app, name="meetings")


@meetings_app.command("link")
def meetings_link(
    provider: str = typer.Option(..., "--provider", "-p"),
    topic: str = typer.Option(..., "--topic", "-t"),
    duration: int = typer.Option(60, "--duration", "-d"),
) -> None:
    client = _client()
    try:
        result = client.calendar.generate_meeting_link(provider, topic, duration)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        data = result.get("data", {})
        console.print("[green]✓[/green] Meeting link generated")
        console.print(f"  Link: {data.get('link')}")
        console.print(f"  Provider: {data.get('provider', provider)}")
    except HireSquireError as exc:
        _handle_error(exc, "meetings link")


# ---------------------------------------------------------------------------
# estimate
# ---------------------------------------------------------------------------


@app.command()
def estimate(
    candidates: int = typer.Option(10, "--candidates", "-c"),
) -> None:
    """Estimate screening cost."""
    client = _client()
    try:
        result = client.credits.estimate_cost(candidates)
        if _JSON_OUTPUT[0]:
            _json(result)
            return
        console.print("[blue]Cost Estimate[/blue]")
        console.print(f"  Candidates: {result.get('candidate_count')}")
        console.print(f"  Cost per candidate: ${result.get('cost_per_candidate')}")
        console.print(f"  [bold]Total: ${result.get('total_cost')}[/bold]")
    except HireSquireError as exc:
        _handle_error(exc, "estimate")


# ---------------------------------------------------------------------------
# mcp (FastMCP stdio server)
# ---------------------------------------------------------------------------


@app.command()
def mcp() -> None:
    """Start the MCP server (stdio) for Claude Desktop and MCP-compatible agents."""
    from .mcp_server import main as mcp_main

    mcp_main()


# Colon-separated command aliases for parity with the TypeScript CLI.
app.command(name="calendar:connect", hidden=True)(calendar_connect)
app.command(name="calendar:list", hidden=True)(calendar_list)
app.command(name="interviews:schedule", hidden=True)(interviews_schedule)
app.command(name="interviews:list", hidden=True)(interviews_list)
app.command(name="meetings:link", hidden=True)(meetings_link)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
