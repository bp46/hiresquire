"""Shared HTTP client for the HireSquire SDK.

Single source of truth for authentication, retry/backoff, idempotency, and
error mapping. Used by the SDK client, CLI, and MCP server alike.
"""

import time
import uuid
from typing import Any, Dict, Optional, Type

import httpx

from . import __version__
from .config import Config
from .errors import (
    AuthenticationError,
    HireSquireError,
    NotFoundError,
    PaymentRequiredError,
    RateLimitError,
    ValidationError,
)

DEFAULT_BASE_URL = "https://hiresquireai.com/api/v1"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds base delay

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _build_user_agent() -> str:
    return f"HireSquirePython/{__version__}"


class HttpClient:
    def __init__(
        self,
        api_token: Optional[str] = None,
        base_url: Optional[str] = None,
        config: Optional[Config] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        cfg = config or Config.load()
        self.api_token = api_token or cfg.api_token
        self.base_url = (base_url or cfg.base_url or DEFAULT_BASE_URL).rstrip("/")
        if not self.base_url:
            self.base_url = DEFAULT_BASE_URL

        if not self.api_token:
            raise AuthenticationError(
                "HireSquire API token is required. Provide it explicitly or set "
                "HIRESQUIRE_API_TOKEN (or ~/.hiresquire/config.json)."
            )

        self._client = httpx.Client(
            base_url=self.base_url + "/",
            timeout=timeout,
            headers=self._default_headers(),
        )

    def _default_headers(self, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": _build_user_agent(),
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def _handle_error(self, response: httpx.Response) -> HireSquireError:
        try:
            data = response.json()
        except Exception:
            data = {}
        message = (
            data.get("message")
            or data.get("error")
            or data.get("detail")
            or response.text
            or f"HTTP {response.status_code}"
        )
        code = data.get("code")
        status = response.status_code

        if status in (401, 403):
            return AuthenticationError(message, status_code=status, response=data)
        if status == 402:
            return PaymentRequiredError(message, status_code=status, response=data)
        if status == 404:
            return NotFoundError(message, status_code=status, response=data)
        if status == 429:
            retry_after = response.headers.get("retry-after")
            msg = message
            if retry_after:
                msg = f"{message} Retry after {retry_after} seconds."
            return RateLimitError(msg, status_code=status, response=data)
        if status in (400, 422):
            return ValidationError(message, status_code=status, code=code, response=data)
        return HireSquireError(message, status_code=status, code=code, response=data)

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_exception: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.request(method, url, **kwargs)
            except (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.ConnectTimeout,
                httpx.NetworkError,
            ) as exc:
                last_exception = exc
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (2**attempt))
                    continue
                raise HireSquireError(str(exc), code="NETWORK_ERROR") from exc

            if response.status_code in RETRYABLE_STATUS_CODES:
                if response.status_code == 429:
                    retry_after = response.headers.get("retry-after", str(RETRY_DELAY * 4))
                    try:
                        delay = int(retry_after)
                    except (ValueError, TypeError):
                        delay = RETRY_DELAY * 4
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(delay)
                        continue
                elif 500 <= response.status_code < 600:
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAY * (2**attempt)
                        time.sleep(delay)
                        continue

            if response.is_success:
                return response

            raise self._handle_error(response)

        if last_exception:
            raise HireSquireError(str(last_exception), code="NETWORK_ERROR") from last_exception
        raise HireSquireError("Request failed after retries", code="REQUEST_FAILED")

    def get(
        self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> httpx.Response:
        return self._request_with_retry("GET", url, params=params, **kwargs)

    def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        merged_headers = self._default_headers(idempotency_key=idempotency_key)
        if headers:
            merged_headers.update(headers)
        # For multipart uploads, let httpx set the content-type boundary.
        if files and "Content-Type" in merged_headers:
            del merged_headers["Content-Type"]
        return self._request_with_retry(
            "POST", url, json=json, data=data, files=files, headers=merged_headers, **kwargs
        )

    def put(self, url: str, json: Optional[Dict[str, Any]] = None, **kwargs: Any) -> httpx.Response:
        return self._request_with_retry("PUT", url, json=json, **kwargs)

    def patch(
        self, url: str, json: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> httpx.Response:
        return self._request_with_retry("PATCH", url, json=json, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return self._request_with_retry("DELETE", url, **kwargs)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[object],
    ) -> None:
        self.close()


def generate_idempotency_key() -> str:
    return str(uuid.uuid4())
