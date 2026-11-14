# Changelog

All notable changes to `hiresquire` are documented in this file.

## [2.0.1] - 2026-11-14

### Improved
- Expanded `README.md` with full MCP tool reference, CLI command table, SDK namespaces, JSON request/response schemas, error hierarchy, and `uvx` quickstarts for AI agents.
- Added `glama.json` (Glama MCP ownership) and `server.json` (Official MCP Registry manifest).
- Added PyPI `keywords` and `classifiers` in `pyproject.toml` for improved package discoverability.
- Added runnable examples in `examples/`.

## [2.0.0] - 2026-11-13

### Added
- Unified Python SDK (`HireSquireClient`), Typer CLI (`hiresquire`), and FastMCP stdio server (`hiresquire-mcp`) in a single package.
- Pydantic v2 request/response models in `hiresquire.models`.
- Shared `HttpClient` with automatic retries, `Retry-After` backoff, and `Idempotency-Key` support.
- Bundled local resume parsing (`pypdf`, `python-docx`, `.txt`, `.md`) with 20 MB per-file and 100-resume batch limits.
- Backward-compatible `HireSquire` alias and deprecated v1 top-level function wrappers.
