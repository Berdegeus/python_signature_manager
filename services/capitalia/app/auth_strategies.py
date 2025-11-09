from __future__ import annotations

"""Authentication strategy abstractions for the HTTP handler pipeline."""

from abc import ABC, abstractmethod
from typing import Dict, Any

from ..adapters.jwt_auth import verify as jwt_verify


class AuthStrategy(ABC):
    """Defines the contract for authentication strategies.

    Implementations must validate the provided credential/token and return the
    claims information associated with the request. Errors should be surfaced
    by raising an exception with a meaningful message so the handler can
    propagate it to the HTTP response.
    """

    @abstractmethod
    def authenticate(self, token: str) -> Dict[str, Any]:
        """Validate the incoming token and return the associated claims."""


class JwtAuthStrategy(AuthStrategy):
    """Authenticates requests using JWT tokens signed with HS256."""

    def __init__(self, secret: str) -> None:
        self._secret = secret

    def authenticate(self, token: str) -> Dict[str, Any]:  # noqa: D401 - short delegate
        return jwt_verify(token, self._secret)
