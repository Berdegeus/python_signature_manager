from __future__ import annotations

from abc import ABC
from datetime import date, timedelta
from typing import Dict, TYPE_CHECKING

from .errors import ValidationError


if TYPE_CHECKING:
    from .models import User


class UserState(ABC):
    name: str

    def evaluate(self, user: "User", today: date) -> str:
        return self.name

    def upgrade(self, user: "User") -> None:
        raise ValidationError("only basic|trial can upgrade to premium")

    def downgrade(self, user: "User") -> None:
        raise ValidationError("only premium can downgrade to basic")

    def suspend(self, user: "User") -> None:
        raise ValidationError("only premium can be suspended")

    def reactivate(self, user: "User") -> None:
        raise ValidationError("only suspended premium can reactivate")


class ActiveState(UserState):
    name = "active"

    def evaluate(self, user: "User", today: date) -> str:
        if user.plan == "basic":
            return self.name
        if user.plan == "trial":
            if user.start_date + timedelta(days=30) <= today:
                return "expired"
            return self.name
        return self.name

    def upgrade(self, user: "User") -> None:
        if user.plan not in ("basic", "trial"):
            raise ValidationError("only basic|trial can upgrade to premium")
        user.plan = "premium"
        user.status = "active"

    def downgrade(self, user: "User") -> None:
        if user.plan != "premium":
            raise ValidationError("only premium can downgrade to basic")
        user.plan = "basic"
        user.status = "active"

    def suspend(self, user: "User") -> None:
        if user.plan != "premium":
            raise ValidationError("only premium can be suspended")
        user.status = "suspended"


class SuspendedState(UserState):
    name = "suspended"

    def evaluate(self, user: "User", today: date) -> str:  # noqa: ARG002
        return self.name

    def downgrade(self, user: "User") -> None:
        if user.plan != "premium":
            raise ValidationError("only premium can downgrade to basic")
        user.plan = "basic"
        user.status = "active"

    def reactivate(self, user: "User") -> None:
        if user.plan != "premium":
            raise ValidationError("only suspended premium can reactivate")
        user.status = "active"


class ExpiredState(UserState):
    name = "expired"

    def evaluate(self, user: "User", today: date) -> str:  # noqa: ARG002
        return self.name

    def upgrade(self, user: "User") -> None:
        if user.plan not in ("basic", "trial"):
            raise ValidationError("only basic|trial can upgrade to premium")
        user.plan = "premium"
        user.status = "active"


_STATE_REGISTRY: Dict[str, UserState] = {
    "active": ActiveState(),
    "suspended": SuspendedState(),
    "expired": ExpiredState(),
}


def get_user_state(status: str) -> UserState:
    try:
        return _STATE_REGISTRY[status]
    except KeyError as exc:  # pragma: no cover - defensive branch
        raise ValidationError(f"unknown status '{status}'") from exc


def resolve_state_for(user: "User") -> UserState:
    if user.plan in ("basic", "trial"):
        return _STATE_REGISTRY["active"]
    return get_user_state(user.status)
