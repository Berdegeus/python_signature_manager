from __future__ import annotations

import hashlib
import json
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

import pytest

from libs.python.data_access import SqlUnitOfWork
from libs.python.http_core import HttpRequest
from services.capitalia.adapters.jwt_auth import verify as jwt_verify
from services.capitalia.adapters.sqlite_repo import SqliteUserRepository
from services.capitalia.app.handlers import build_handler


@dataclass
class _SetupResult:
    uow_factory: Callable[[], SqlUnitOfWork]
    email: str
    password: str
    user_id: int
    clock_today: date


class FixedClock:
    def __init__(self, today: date) -> None:
        self._today = today

    def today(self) -> date:
        return self._today


@pytest.fixture
def sqlite_app(tmp_path) -> _SetupResult:
    db_path = tmp_path / "capitalia.db"
    email = "alice@example.com"
    password = "password123"
    salt = "static-salt"
    start_date = date(2024, 1, 1)
    clock_today = start_date + timedelta(days=45)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                plan TEXT NOT NULL,
                start_date TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        password_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        cur = conn.execute(
            """
            INSERT INTO users (name, email, password_hash, salt, plan, start_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("Alice", email, password_hash, salt, "trial", start_date.isoformat(), "active"),
        )
        user_id = int(cur.lastrowid)
        conn.commit()

    def conn_factory() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def repo_factory(conn: sqlite3.Connection) -> SqliteUserRepository:
        return SqliteUserRepository(conn)

    return _SetupResult(
        uow_factory=lambda: SqlUnitOfWork(conn_factory, repo_factory),
        email=email,
        password=password,
        user_id=user_id,
        clock_today=clock_today,
    )


def _make_request(
    method: str,
    target: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes = b"",
) -> HttpRequest:
    return HttpRequest(
        method=method,
        target=target,
        path=target,
        query="",
        headers=headers or {},
        body=body,
        client=("127.0.0.1", 0),
    )


def test_full_flow_over_sqlite(sqlite_app: _SetupResult) -> None:
    secret = "integration-secret"
    processor = build_handler(sqlite_app.uow_factory, secret, FixedClock(sqlite_app.clock_today))

    login_body = json.dumps({"email": sqlite_app.email, "password": sqlite_app.password}).encode()
    login_request = _make_request(
        "POST",
        "/login",
        headers={"content-type": "application/json"},
        body=login_body,
    )
    login_response = processor.handle(login_request)

    assert login_response.status == 200
    login_payload = json.loads(login_response.body.decode())
    token = login_payload["token"]
    claims = jwt_verify(token, secret)
    assert claims["sub"] == sqlite_app.user_id

    auth_header = {"authorization": f"Bearer {token}"}
    status_request = _make_request(
        "GET",
        f"/user/{sqlite_app.user_id}/status",
        headers=auth_header,
    )
    status_response = processor.handle(status_request)

    assert status_response.status == 200
    status_payload = json.loads(status_response.body.decode())
    assert status_payload == {
        "user_id": sqlite_app.user_id,
        "plan": "trial",
        "status": "expired",
    }

    upgrade_request = _make_request(
        "POST",
        f"/user/{sqlite_app.user_id}/upgrade",
        headers=auth_header,
    )
    upgrade_response = processor.handle(upgrade_request)

    assert upgrade_response.status == 200
    upgrade_payload = json.loads(upgrade_response.body.decode())
    assert upgrade_payload == {
        "user_id": sqlite_app.user_id,
        "plan": "premium",
        "status": "active",
    }
