from __future__ import annotations

from datetime import date, timedelta

import pytest

from capitalia.domain.errors import ValidationError
from capitalia.domain.models import User
from capitalia.domain.services import SubscriptionService
from capitalia.ports.clock import Clock


class FakeClock(Clock):
    def __init__(self, today: date) -> None:
        self._today = today

    def today(self) -> date:
        return self._today


class FakeRepo:
    def __init__(self, users):
        self._by_id = {u.id: u for u in users}

    def get_by_id(self, user_id):
        return self._by_id.get(user_id)

    def save(self, user):
        self._by_id[user.id] = user


class FakeUoW:
    def __init__(self, repo: FakeRepo):
        self.repo = repo
        self.committed = False
        self.users = None

    def __enter__(self):
        self.users = self.repo
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def commit(self):
        self.committed = True


def make_service(uow):
    return SubscriptionService(lambda: uow, FakeClock(date.today()))


def test_upgrade_from_trial():
    user = User(1, "A", "a@a", "h", "s", "trial", date.today(), "active")
    repo = FakeRepo([user])
    service = make_service(FakeUoW(repo))

    result = service.upgrade(1)

    assert result["plan"] == "premium"
    assert result["status"] == "active"


def test_upgrade_from_expired_trial():
    start = date.today() - timedelta(days=40)
    user = User(1, "A", "a@a", "h", "s", "trial", start, "expired")
    repo = FakeRepo([user])
    service = make_service(FakeUoW(repo))

    result = service.upgrade(1)

    assert result["plan"] == "premium"
    assert result["status"] == "active"


def test_upgrade_from_premium_forbidden():
    user = User(1, "A", "a@a", "h", "s", "premium", date.today(), "active")
    repo = FakeRepo([user])
    service = make_service(FakeUoW(repo))

    with pytest.raises(ValidationError):
        service.upgrade(1)


def test_downgrade_from_premium():
    user = User(1, "A", "a@a", "h", "s", "premium", date.today(), "suspended")
    repo = FakeRepo([user])
    service = make_service(FakeUoW(repo))

    result = service.downgrade(1)

    assert result["plan"] == "basic"
    assert result["status"] == "active"


def test_downgrade_from_basic_forbidden():
    user = User(1, "A", "a@a", "h", "s", "basic", date.today(), "active")
    repo = FakeRepo([user])
    service = make_service(FakeUoW(repo))

    with pytest.raises(ValidationError):
        service.downgrade(1)


def test_suspend_from_premium_active():
    user = User(1, "A", "a@a", "h", "s", "premium", date.today(), "active")
    repo = FakeRepo([user])
    service = make_service(FakeUoW(repo))

    result = service.suspend(1)

    assert result["status"] == "suspended"


def test_suspend_from_basic_forbidden():
    user = User(1, "A", "a@a", "h", "s", "basic", date.today(), "active")
    repo = FakeRepo([user])
    service = make_service(FakeUoW(repo))

    with pytest.raises(ValidationError):
        service.suspend(1)


def test_reactivate_from_suspended_premium():
    user = User(1, "A", "a@a", "h", "s", "premium", date.today(), "suspended")
    repo = FakeRepo([user])
    service = make_service(FakeUoW(repo))

    result = service.reactivate(1)

    assert result["status"] == "active"


def test_reactivate_from_active_forbidden():
    user = User(1, "A", "a@a", "h", "s", "premium", date.today(), "active")
    repo = FakeRepo([user])
    service = make_service(FakeUoW(repo))

    with pytest.raises(ValidationError):
        service.reactivate(1)


def test_read_effective_status_updates_expired_trial():
    start = date.today() - timedelta(days=40)
    user = User(1, "A", "a@a", "h", "s", "trial", start, "active")
    repo = FakeRepo([user])
    uow = FakeUoW(repo)
    service = SubscriptionService(lambda: uow, FakeClock(date.today()))

    result = service.read_effective_status(1)

    assert result["status"] == "expired"
    assert repo.get_by_id(1).status == "expired"
