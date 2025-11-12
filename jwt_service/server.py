from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from .config import JwtServiceConfig
from .tokens import sign


class JwtRequestHandler(BaseHTTPRequestHandler):
    config: JwtServiceConfig

    def do_GET(self) -> None:  # pragma: no cover - simple healthcheck
        if self.path.rstrip("/") == "/health":
            self._write_json(HTTPStatus.OK, {"status": "ok"})
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/token":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "invalid content-length"})
            return

        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode() or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "invalid json"})
            return

        claims = payload.get("claims")
        if not isinstance(claims, dict):
            self._write_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "claims must be an object"})
            return

        ttl = self._coerce_ttl(payload.get("ttl"))
        if ttl is None:
            return

        token = sign(claims, self.config.secret, ttl_seconds=ttl)
        self._write_json(HTTPStatus.OK, {"token": token})

    def log_message(self, format: str, *args) -> None:  # pragma: no cover - disable noisy logs
        return

    def _coerce_ttl(self, raw_ttl) -> Optional[int]:
        if raw_ttl is None:
            return self.config.default_ttl
        try:
            ttl = int(raw_ttl)
        except (TypeError, ValueError):
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "ttl must be an integer"})
            return None
        if ttl <= 0:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "ttl must be positive"})
            return None
        return ttl

    def _write_json(self, status: HTTPStatus, data) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(config: JwtServiceConfig) -> HTTPServer:
    handler_cls = type("ConfiguredJwtRequestHandler", (JwtRequestHandler,), {})
    handler_cls.config = config
    return HTTPServer((config.host, config.port), handler_cls)


__all__ = ["create_server", "JwtRequestHandler"]
