from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict


class TokenIssueError(RuntimeError):
    """Raised when the token service cannot issue a token."""


@dataclass
class JwtTokenClient:
    base_url: str
    timeout: float = 5.0

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    def issue_token(self, claims: Dict[str, Any], ttl_seconds: int = 3600) -> str:
        payload = json.dumps({"claims": claims, "ttl": ttl_seconds}).encode()
        request = urllib.request.Request(
            f"{self.base_url}/token",
            data=payload,
            method="POST",
            headers={"content-type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                status = response.getcode()
        except urllib.error.HTTPError as exc:  # pragma: no cover - network errors
            raise TokenIssueError(f"token service returned {exc.code}") from exc
        except urllib.error.URLError as exc:  # pragma: no cover - network errors
            raise TokenIssueError("unable to reach token service") from exc

        if status != 200:
            raise TokenIssueError(f"unexpected status code {status}")

        try:
            data = json.loads(body.decode() or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TokenIssueError("invalid response from token service") from exc

        token = data.get("token")
        if not isinstance(token, str):
            raise TokenIssueError("token service response missing token")
        return token


__all__ = ["JwtTokenClient", "TokenIssueError"]
