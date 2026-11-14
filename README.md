# HireSquire

Unified open-source Python package for HireSquire's AI-powered candidate
screening API. One install gives you the SDK, CLI, and MCP server:

```bash
pip install hiresquire
# or without installing:
uvx hiresquire screen --title "Senior Developer" --description "..." --resumes ./resumes/
```

## Installation

```bash
pip install hiresquire
```

## Quick Start

### Python SDK

```python
from hiresquire import HireSquireClient

client = HireSquireClient("YOUR_API_TOKEN")

job = client.screen(
    title="Senior Python Developer",
    description="Looking for experienced Python developer...",
    resumes=["./resumes/john_doe.pdf", "./resumes/jane_smith.pdf"],
)
results = client.wait_for_completion(job["job_id"])

for candidate in results["candidates"]:
    print(f"{candidate['name']}: {candidate['score']}/100")
```

### CLI

```bash
# Configure your token
hiresquire init --token YOUR_API_TOKEN

# Screen resumes (watch for completion, JSON output)
hiresquire screen \
  --title "Senior Developer" \
  --description "We're hiring..." \
  --resumes ./resumes/ \
  --watch \
  --json

# View results
hiresquire results --job 123 --min-score 80 --only-top-n 5
```

### MCP server (Claude Desktop, VS Code, etc.)

```bash
hiresquire mcp
```

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hiresquire": {
      "command": "hiresquire-mcp",
      "env": {
        "HIRESQUIRE_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `HIRESQUIRE_API_TOKEN` | API token from HireSquire dashboard |
| `HIRESQUIRE_BASE_URL` | API base URL (default: https://hiresquireai.com/api/v1) |
| `HIRESQUIRE_WEBHOOK_URL` | Default webhook URL |

Config is also persisted to `~/.hiresquire/config.json` (mode 0600) via `hiresquire init`.

## Backward Compatibility (v1 → v2)

`HireSquire` remains an alias for `HireSquireClient`, and the v1 top-level
functions (`create_screening_job`, `get_hiresquire_tools`, etc.) are preserved
as thin deprecated wrappers so existing v1 code keeps working:

```python
from hiresquire import HireSquire  # alias for HireSquireClient
from hiresquire import create_screening_job  # deprecated wrapper
```

## Repository

Public open-source client repo: https://github.com/bp46/hiresquire  
Private SaaS backend (closed-source): `bp46/hiresquire-web`

## License

MIT License — see LICENSE file.
