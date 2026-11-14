# Security Policy

## Supported versions

Only the latest major version of `hiresquire` receives security updates.

## Reporting a vulnerability

Please disclose security vulnerabilities responsibly by emailing
info@hiresquireai.com. Do not open public issues for security concerns.

## Client-side security notes

- Never commit `HIRESQUIRE_API_TOKEN` or Agent API keys (`hs_...`) to version control.
- Prefer environment variables over `~/.hiresquire/config.json` on shared systems.
- The config file is written with mode 0600 (owner read/write only).
- Resume text is sent to the HireSquire API; do not log resume contents or candidate PII.
- The default API base URL is `https://hiresquireai.com/api/v1` and can be overridden via
  `HIRESQUIRE_BASE_URL`. No internal URLs are hardcoded in client code.
