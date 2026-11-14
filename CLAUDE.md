# HireSquire — Claude / MCP instructions

Add the HireSquire MCP server to Claude Desktop via `hiresquire-mcp` (stdio).

## Claude Desktop config

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hiresquire": {
      "command": "hiresquire-mcp",
      "env": {
        "HIRESQUIRE_API_TOKEN": "your_api_token_here",
        "HIRESQUIRE_BASE_URL": "https://hiresquireai.com/api/v1"
      }
    }
  }
}
```

Or install without `npx`:

```bash
pip install hiresquire
# then the `hiresquire-mcp` command is on PATH
```

## Auth

Set `HIRESQUIRE_API_TOKEN` (from the HireSquire dashboard /profile → API Tokens).
`whoami()` is a free health check — call it first to verify token + credits.

## Key tools for Claude

- `create_screening(title, description, resume_paths?, resumes?, leniency_level)` — screen resumes. Pass `resume_paths` for local PDF/DOCX/TXT/MD files (parsed client-side) or `resumes` for pre-parsed content.
- `get_screening_status(job_id)` — poll status
- `get_results(job_id, min_score, only_top_n)` — candidate scores
- `generate_email(job_id, candidate_id, type, tone)` — outreach email
- `create_interview(job_id, candidate_id, scheduled_at)` — schedule
- `whoami()` — profile + balance
- `audit_screening_job(job_id, selection_threshold)` — bias/EEOC audit

## Async pattern

Screening is async: create → poll status → get results. Use `get_screening_status`
until `completed`, then `get_results`.

## Repo

https://github.com/bp46/hiresquire (open-source client)  
Backend: `bp46/hiresquire-web` (private SaaS)
