from __future__ import annotations

from typing import Any, Dict

from jwt_service.tokens import verify as _verify


def verify(token: str, secret: str) -> Dict[str, Any]:
    """Validate a JWT issued by the token service."""
    return _verify(token, secret)


__all__ = ["verify"]
