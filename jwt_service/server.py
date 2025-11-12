from __future__ import annotations

import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from config import JwtServiceConfig
from tokens import sign


class JwtRequestHandler(BaseHTTPRequestHandler):
    config: JwtServiceConfig
    logger = logging.getLogger("jwt_service.server")

    def do_GET(self) -> None:  # pragma: no cover - simple healthcheck
        if self.path.rstrip("/") == "/health":
            self._write_json(HTTPStatus.OK, {"status": "ok"})
            return
        self._write_error(HTTPStatus.NOT_FOUND, "not found")

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/token":
            self._write_error(HTTPStatus.NOT_FOUND, "not found")
            return

        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError:
            self._write_error(HTTPStatus.BAD_REQUEST, "invalid content-length")
            return

        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode() or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write_error(HTTPStatus.BAD_REQUEST, "invalid json payload")
            return

        claims = payload.get("claims")
        if not isinstance(claims, dict):
            self._write_error(HTTPStatus.UNPROCESSABLE_ENTITY, "claims must be an object")
            return

        ttl = self._coerce_ttl(payload.get("ttl"))
        if ttl is None:
            return

        token = sign(claims, self.config.secret, ttl_seconds=ttl)
        claim_keys = ", ".join(sorted(map(str, claims.keys()))) or "<empty>"
        self.logger.info(
            "issued token for %s (ttl=%s, claim keys=%s)",
            self.client_address[0],
            ttl,
            claim_keys,
        )
        self._write_json(HTTPStatus.OK, {"token": token})

    def log_message(self, format: str, *args) -> None:  # pragma: no cover - structured logging
        self.logger.info("%s - %s", self.address_string(), format % args)

    def _coerce_ttl(self, raw_ttl) -> Optional[int]:
        if raw_ttl is None:
            return self.config.default_ttl
        try:
            ttl = int(raw_ttl)
        except (TypeError, ValueError):
            self._write_error(HTTPStatus.BAD_REQUEST, "ttl must be an integer")
            return None
        if ttl <= 0:
            self._write_error(HTTPStatus.BAD_REQUEST, "ttl must be positive")
            return None
        return ttl

    def _write_json(self, status: HTTPStatus, data) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_error(self, status: HTTPStatus, message: str) -> None:
        self.logger.warning(
            "request from %s failed with %s: %s",
            self.client_address[0],
            status,
            message,
        )
        self._write_json(status, {"error": message})


def create_server(config: JwtServiceConfig) -> HTTPServer:
    handler_cls = type("ConfiguredJwtRequestHandler", (JwtRequestHandler,), {})
    handler_cls.config = config
    return HTTPServer((config.host, config.port), handler_cls)


__all__ = ["create_server", "JwtRequestHandler"]
