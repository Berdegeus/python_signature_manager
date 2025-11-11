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
        raise ValidationError("apenas planos basic ou trial podem atualizar para premium")

    def downgrade(self, user: "User") -> None:
        raise ValidationError("apenas usuários premium podem realizar downgrade para basic")

    def suspend(self, user: "User") -> None:
        raise ValidationError("apenas assinaturas premium podem ser suspensas")

    def reactivate(self, user: "User") -> None:
        raise ValidationError("somente assinaturas premium suspensas podem ser reativadas")


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
            raise ValidationError("apenas planos basic ou trial podem atualizar para premium")
        user.plan = "premium"
        user.status = "active"

    def downgrade(self, user: "User") -> None:
        if user.plan != "premium":
            raise ValidationError("apenas usuários premium podem realizar downgrade para basic")
        user.plan = "basic"
        user.status = "active"

    def suspend(self, user: "User") -> None:
        if user.plan != "premium":
            raise ValidationError("apenas assinaturas premium podem ser suspensas")
        user.status = "suspended"


class SuspendedState(UserState):
    name = "suspended"

    def evaluate(self, user: "User", today: date) -> str:  # noqa: ARG002
        return self.name

    def downgrade(self, user: "User") -> None:
        if user.plan != "premium":
            raise ValidationError("apenas usuários premium podem realizar downgrade para basic")
        user.plan = "basic"
        user.status = "active"

    def reactivate(self, user: "User") -> None:
        if user.plan != "premium":
            raise ValidationError("somente assinaturas premium suspensas podem ser reativadas")
        user.status = "active"


class ExpiredState(UserState):
    name = "expired"

    def evaluate(self, user: "User", today: date) -> str:  # noqa: ARG002
        return self.name

    def upgrade(self, user: "User") -> None:
        if user.plan not in ("basic", "trial"):
            raise ValidationError("apenas planos basic ou trial podem atualizar para premium")
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
        raise ValidationError(f"status desconhecido '{status}'") from exc


def resolve_state_for(user: "User") -> UserState:
    if user.plan in ("basic", "trial"):
        return _STATE_REGISTRY["active"]
    return get_user_state(user.status)
