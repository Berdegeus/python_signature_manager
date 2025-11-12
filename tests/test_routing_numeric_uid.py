from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from capitalia.app.handlers import build_handler
from capitalia.app.http import HttpRequest
from capitalia.domain.models import User
from jwt_service.tokens import sign as jwt_sign


class FakeTokenClient:
    def __init__(self, secret: str) -> None:
        self.secret = secret
        self.calls: list[dict[str, object]] = []

    def issue_token(self, claims: dict[str, object], ttl_seconds: int = 3600) -> str:
        self.calls.append({"claims": claims, "ttl": ttl_seconds})
        return jwt_sign(claims, self.secret, ttl_seconds)


@dataclass
class FakeUsersRepository:
    user: User

    def get_by_email(self, email: str) -> User | None:  # pragma: no cover - trivial
        if self.user and self.user.email == email:
            return self.user
        return None

    def get_by_id(self, uid: int) -> User | None:  # pragma: no cover - trivial
        if self.user and self.user.id == uid:
            return self.user
        return None

    def save(self, user: User) -> None:  # pragma: no cover - trivial
        self.user = user


class FakeUnitOfWork:
    def __init__(self, user: User) -> None:
        self.users = FakeUsersRepository(user)

    def __enter__(self) -> "FakeUnitOfWork":  # pragma: no cover - trivial
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # pragma: no cover - trivial
        return False

    def commit(self) -> None:  # pragma: no cover - trivial
        pass


class FakeClock:
    def today(self) -> date:  # pragma: no cover - trivial
        return date(2024, 1, 1)


def test_user_status_route_accepts_numeric_uid() -> None:
    user = User(
        id=1,
        name="Alice",
        email="alice@example.com",
        password_hash="hash",
        salt="salt",
        plan="premium",
        start_date=date(2023, 1, 1),
        status="active",
    )

    def uow_factory() -> FakeUnitOfWork:
        return FakeUnitOfWork(user)

    secret = "secret"
    token_client = FakeTokenClient(secret)
    processor = build_handler(uow_factory, secret, FakeClock(), token_client=token_client)

    token = jwt_sign({"sub": user.id, "email": user.email, "plan": user.plan}, secret)
    request = HttpRequest(
        method="GET",
        target="/user/1/status",
        path="/user/1/status",
        query="",
        headers={"authorization": f"Bearer {token}"},
        body=b"",
        client=("127.0.0.1", 0),
    )

    response = processor.handle(request)

    assert response.status == 200
    payload = json.loads(response.body.decode())
    assert payload["user_id"] == 1

