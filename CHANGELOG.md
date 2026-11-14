# Changelog

All notable changes to `hiresquire` are documented in this file.

## [2.0.0] - 2026-11-13

### Added
- Unified Python SDK (`HireSquireClient`), Typer CLI (`hiresquire`), and FastMCP stdio server (`hiresquire-mcp`) in a single package.
- Pydantic v2 request/response models in `hiresquire.models`.
- Shared `HttpClient` with automatic retries, `Retry-After` backoff, and `Idempotency-Key` support.
- Bundled local resume parsing (`pypdf`, `python-docx`, `.txt`, `.md`) with 20 MB per-file and 100-resume batch limits.
- Backward-compatible `HireSquire` alias and deprecated v1 top-level function wrappers.

