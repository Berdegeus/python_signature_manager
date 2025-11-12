from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class JwtServiceConfig:
    host: str
    port: int
    secret: str
    default_ttl: int


def load_config() -> JwtServiceConfig:
    host = os.environ.get("JWT_SERVICE_HOST", "0.0.0.0")
    port = int(os.environ.get("JWT_SERVICE_PORT", "8200"))
    secret = os.environ.get("JWT_SECRET", "change-me")
    default_ttl = int(os.environ.get("JWT_DEFAULT_TTL", "3600"))
    return JwtServiceConfig(host=host, port=port, secret=secret, default_ttl=default_ttl)


__all__ = ["JwtServiceConfig", "load_config"]
