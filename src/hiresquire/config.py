"""Configuration management shared by SDK, CLI, and MCP server.

Precedence: environment variables > ~/.hiresquire/config.json > defaults.
"""

import json
import os
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".hiresquire"
CONFIG_FILE = CONFIG_DIR / "config.json"

ENV_TOKEN = "HIRESQUIRE_API_TOKEN"
ENV_BASE_URL = "HIRESQUIRE_BASE_URL"
ENV_WEBHOOK_URL = "HIRESQUIRE_WEBHOOK_URL"

DEFAULT_BASE_URL = "https://hiresquireai.com/api/v1"


class Config:
    def __init__(
        self,
        api_token: Optional[str] = None,
        base_url: Optional[str] = None,
        webhook_url: Optional[str] = None,
        default_leniency: int = 5,
    ):
        self.api_token = api_token or ""
        self.base_url = base_url or DEFAULT_BASE_URL
        self.webhook_url = webhook_url
        self.default_leniency = default_leniency

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        path = Path(config_path) if config_path else CONFIG_FILE

        # Env vars take highest precedence.
        api_token = os.environ.get(ENV_TOKEN, "")
        env_base_url = os.environ.get(ENV_BASE_URL, "")
        webhook_url = os.environ.get(ENV_WEBHOOK_URL)

        file_cfg: dict = {}
        if path.exists():
            try:
                file_cfg = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                file_cfg = {}

        if not api_token:
            api_token = file_cfg.get("api_token", "") or ""
        base_url = env_base_url or file_cfg.get("base_url") or DEFAULT_BASE_URL
        if webhook_url is None:
            webhook_url = file_cfg.get("webhook_url")

        return cls(
            api_token=api_token or None,
            base_url=base_url,
            webhook_url=webhook_url,
            default_leniency=file_cfg.get("default_leniency", 5),
        )

    def save(self, config_path: Optional[str] = None) -> None:
        path = Path(config_path) if config_path else CONFIG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "api_token": self.api_token,
            "base_url": self.base_url,
            "webhook_url": self.webhook_url,
            "default_leniency": self.default_leniency,
        }
        payload = json.dumps(data, indent=2)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.chmod(path, 0o600)
        except OSError:
            path.write_text(payload, encoding="utf-8")
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass

    def clear(self, config_path: Optional[str] = None) -> None:
        path = Path(config_path) if config_path else CONFIG_FILE
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    def is_configured(self) -> bool:
        return bool(self.api_token)
