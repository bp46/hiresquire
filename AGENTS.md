# HireSquire Agent Integration

Quick reference for AI agents and autonomous systems integrating with the
open-source `hiresquire` Python package (SDK + CLI + MCP server).

Repo: https://github.com/bp46/hiresquire  
Package: https://pypi.org/project/hiresquire/  
Private SaaS backend (closed): `bp46/hiresquire-web`

## Install

```bash
pip install hiresquire
# or run without installing:
uvx hiresquire screen --title "..." --description "..." --resumes ./resumes/
```

## Auth

```bash
export HIRESQUIRE_API_TOKEN="your_token"
export HIRESQUIRE_BASE_URL="https://hiresquireai.com/api/v1"  # optional
```

Or run `hiresquire init --token <token>` (saves to `~/.hiresquire/config.json`, mode 0600).

## Python SDK

```python
from hiresquire import HireSquireClient

client = HireSquireClient()
job = client.screen(
    title="Senior Developer",
    description="...",
    resumes=["./resumes/a.pdf", "./resumes/b.txt"],
)
results = client.wait_for_completion(job["job_id"])
```

Namespaces: `client.jobs`, `client.candidates`, `client.credits`, `client.calendar`, `client.agent_keys`, `client.emails`, `client.utils`.

## CLI

All commands support `--json` for machine-readable output.

```bash
hiresquire init --token <token>
hiresquire screen --title "..." --description "..." --resumes ./resumes/ --watch --json
hiresquire results --job 123 --min-score 80 --only-top-n 5
hiresquire whoami --json
hiresquire credits balance
hiresquire calendar:list
hiresquire interviews:schedule --job 123 --candidate 456 --time "2026-05-15T14:00:00Z"
```

## MCP server (stdio)

```bash
hiresquire mcp
```

Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "hiresquire": {
      "command": "hiresquire-mcp",
      "env": { "HIRESQUIRE_API_TOKEN": "your_token" }
    }
  }
}
```

## Async workflow (critical)

Resume screening is asynchronous:

1. `client.jobs.create(...)` → returns `job_id` (status `processing`)
2. Poll `client.jobs.get_status(job_id)` until `status == "completed"`
3. `client.jobs.get_results(job_id)` → candidate scores

Or use `client.jobs.wait(job_id)` / `screen --watch` to block until done.

## MCP tools

Screening: `create_screening`, `get_screening_status`, `get_results`,
`cancel_screening_job`, `compare_candidates`, `report_hiring_outcome`  
Email: `generate_email`, `bulk_generate_emails`  
Credits: `get_credit_balance`, `estimate_screening_cost`, `list_credit_packs`,
`get_credit_transactions`, `purchase_credits`, `create_checkout_session`,
`enable_auto_reload`, `disable_auto_reload`  
Calendar: `list_calendar_connections`, `create_calendar_connection`,
`get_available_slots`, `create_interview`, `generate_meeting_link`  
Utils: `whoami`, `get_rate_limit`, `test_webhook`, `get_api_schema`,
`audit_screening_job`

## v1 → v2 compatibility

`from hiresquire import HireSquire` is an alias for `HireSquireClient`.
V1 top-level functions (`create_screening_job`, `get_hiresquire_tools`, …) are
preserved as deprecated wrappers.

## Support

- Email: info@hiresquireai.com
- API docs: https://hiresquireai.com/docs/api
- Agent docs: https://hiresquireai.com/docs/agents
