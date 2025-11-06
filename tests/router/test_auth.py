from __future__ import annotations

import json
import re
from http import HTTPStatus
from typing import Any, Dict

import pytest

from capitalia.adapters.jwt_auth import sign
from capitalia.app.auth_strategies import AuthStrategy, JwtAuthStrategy
from capitalia.app.handlers import AbstractHandler, AuthHandler, forbidden
from capitalia.app.http import HttpRequest, HttpResponse, RequestContext, Route


class DummyHandler(AbstractHandler):
    """Terminal handler used to assert delegation from ``AuthHandler``."""

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def handle(self, ctx: RequestContext) -> HttpResponse:  # pragma: no cover - trivial
        self.calls += 1
        response = HttpResponse(HTTPStatus.OK, {"Content-Length": "0"}, b"")
        ctx.response = response
        return response


class RecordingStrategy(AuthStrategy):
    """Auth strategy stub that records tokens and yields predefined results."""

    def __init__(self, *, claims: Dict[str, Any] | None = None, error: Exception | None = None) -> None:
        self.tokens: list[str] = []
        self._claims = claims or {}
        self._error = error

    def authenticate(self, token: str) -> Dict[str, Any]:
        self.tokens.append(token)
        if self._error is not None:
            raise self._error
        return self._claims


class FailingStrategy(AuthStrategy):
    def authenticate(self, token: str) -> Dict[str, Any]:
        raise AssertionError("strategy should not be called")


def make_context(
    *,
    requires_auth: bool = True,
    headers: dict | None = None,
    authorize=None,
) -> RequestContext:
    request = HttpRequest(
        method="GET",
        target="/user/1/status",
        path="/user/1/status",
        query="",
        headers=headers or {},
        body=b"",
    )
    ctx = RequestContext(request=request)
    ctx.route = Route(
        "status",
        re.compile(r"^/user/(?P<uid>\\d+)/status$"),
        {"GET"},
        lambda c: HttpResponse(HTTPStatus.OK),
        requires_auth=requires_auth,
        authorize=authorize,
    )
    return ctx


def decode_error(response: HttpResponse) -> str:
    return json.loads(response.body.decode())["error"]


def test_auth_handler_skips_routes_without_auth() -> None:
    strategy = FailingStrategy()
    handler = AuthHandler(strategy)
    next_handler = DummyHandler()
    handler.set_next(next_handler)

    ctx = make_context(requires_auth=False)
    response = handler.handle(ctx)

    assert response.status == HTTPStatus.OK
    assert next_handler.calls == 1


def test_auth_handler_rejects_missing_bearer_token() -> None:
    strategy = RecordingStrategy(claims={"sub": 1})
    handler = AuthHandler(strategy)
    handler.set_next(DummyHandler())

    ctx = make_context(headers={})
    response = handler.handle(ctx)

    assert response.status == HTTPStatus.UNAUTHORIZED
    assert decode_error(response) == "missing bearer token"
    assert strategy.tokens == []


def test_auth_handler_reports_strategy_errors() -> None:
    strategy = RecordingStrategy(error=ValueError("invalid token"))
    handler = AuthHandler(strategy)
    handler.set_next(DummyHandler())

    ctx = make_context(headers={"authorization": "Bearer bad"})
    response = handler.handle(ctx)

    assert response.status == HTTPStatus.UNAUTHORIZED
    assert decode_error(response) == "invalid token"
    assert strategy.tokens == ["bad"]


def test_auth_handler_sets_claims_and_calls_next() -> None:
    expected_claims = {"sub": 1}
    strategy = RecordingStrategy(claims=expected_claims)

    class CheckingHandler(AbstractHandler):
        def __init__(self) -> None:
            super().__init__()
            self.seen_claims = None

        def handle(self, ctx: RequestContext) -> HttpResponse:  # pragma: no cover - trivial
            self.seen_claims = ctx.claims
            response = HttpResponse(HTTPStatus.OK)
            ctx.response = response
            return response

    handler = AuthHandler(strategy)
    next_handler = CheckingHandler()
    handler.set_next(next_handler)

    ctx = make_context(headers={"authorization": "Bearer good"})
    response = handler.handle(ctx)

    assert response.status == HTTPStatus.OK
    assert next_handler.seen_claims == expected_claims
    assert strategy.tokens == ["good"]


def test_auth_handler_honours_authorize_callback() -> None:
    strategy = RecordingStrategy(claims={"sub": "2"})
    handler = AuthHandler(strategy)
    next_handler = DummyHandler()
    handler.set_next(next_handler)

    def authorize(ctx: RequestContext):
        return forbidden("not allowed")

    ctx = make_context(headers={"authorization": "Bearer token"}, authorize=authorize)
    response = handler.handle(ctx)

    assert response.status == HTTPStatus.FORBIDDEN
    assert decode_error(response) == "not allowed"
    assert next_handler.calls == 0


def test_jwt_auth_strategy_validates_tokens() -> None:
    secret = "top-secret"
    token = sign({"sub": 42}, secret, ttl_seconds=60)
    strategy = JwtAuthStrategy(secret)

    claims = strategy.authenticate(token)

    assert claims["sub"] == 42

    with pytest.raises(ValueError):
        JwtAuthStrategy("other").authenticate(token)
