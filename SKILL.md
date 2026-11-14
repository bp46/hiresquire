# HireSquire Agent Skills

You have access to the HireSquire API for AI-powered candidate screening via the
open-source `hiresquire` Python package (SDK + CLI + MCP server).

## Capabilities

- Resume analysis & scoring (1-100) against a job description
- Candidate ranking, comparison, and delta analysis
- Interview question & icebreaker generation
- Outreach email generation (invite / rejection / keep-warm / followup)
- Interview scheduling via Calendly / Cal.com
- Credit management & agent API keys with spend limits
- Automated bias & disparate impact audit (NYC LL144 / EEOC 4/5ths)

## Authentication

All API requests use a Bearer token:

```
Authorization: Bearer YOUR_API_TOKEN
```

Get a token from the HireSquire dashboard (`/profile` → API Tokens). For
autonomous agents, prefer an Agent API Key (`hs_...`) with a spend limit.

## Leniency level (1-10)

| Level | Description | Use case |
|-------|-------------|----------|
| 1-3   | Lenient     | Entry roles, high volume |
| 4-6   | Balanced    | Standard hiring |
| 7-10  | Strict      | Senior / niche roles |

Default: 5.

## Async workflow (POST → poll → GET)

1. `create_screening(...)` → `job_id`
2. Poll `get_screening_status(job_id)` until `completed`
3. `get_results(job_id)` → candidates with scores

## MCP server (stdio)

```bash
hiresquire mcp
# or
uvx hiresquire mcp
```

Tools: `create_screening`, `get_screening_status`, `get_results`,
`generate_email`, `create_interview`, `whoami`, `audit_screening_job`, … (26 tools).

## Repo

https://github.com/bp46/hiresquire — open-source client (MIT)  
https://github.com/bp46/hiresquire-web — private SaaS backend
