from __future__ import annotations

from ..domain.models import User
from ..domain.user_states import get_user_state
from ..domain.errors import NotFoundError
from ..ports.unit_of_work import UnitOfWork
from ..ports.clock import Clock


class SubscriptionService:
    """Casos de uso com transação por operação (UoW)."""

    def __init__(self, uow_factory, clock: Clock):
        self._uow_factory = uow_factory
        self._clock = clock

    def _get_user(self, uow: UnitOfWork, user_id: int) -> User:
        user = uow.users.get_by_id(user_id)
        if not user:
            raise NotFoundError("user not found")
        return user

    def read_effective_status(self, user_id: int) -> dict:
        today = self._clock.today()
        with self._uow_factory() as uow:
            user = self._get_user(uow, user_id)
            state = get_user_state(user.status)
            effective = state.evaluate(user, today)
            if effective != user.status:
                user.status = effective
                uow.users.save(user)
                uow.commit()
            return {"user_id": user.id, "plan": user.plan, "status": effective}

    def upgrade(self, user_id: int) -> dict:
        with self._uow_factory() as uow:
            user = self._get_user(uow, user_id)
            state = get_user_state(user.status)
            state.upgrade(user)
            uow.users.save(user)
            uow.commit()
            return {"user_id": user.id, "plan": user.plan, "status": user.status}

    def downgrade(self, user_id: int) -> dict:
        with self._uow_factory() as uow:
            user = self._get_user(uow, user_id)
            state = get_user_state(user.status)
            state.downgrade(user)
            uow.users.save(user)
            uow.commit()
            return {"user_id": user.id, "plan": user.plan, "status": user.status}

    def suspend(self, user_id: int) -> dict:
        with self._uow_factory() as uow:
            user = self._get_user(uow, user_id)
            state = get_user_state(user.status)
            state.suspend(user)
            uow.users.save(user)
            uow.commit()
            return {"user_id": user.id, "plan": user.plan, "status": user.status}

    def reactivate(self, user_id: int) -> dict:
        with self._uow_factory() as uow:
            user = self._get_user(uow, user_id)
            state = get_user_state(user.status)
            state.reactivate(user)
            uow.users.save(user)
            uow.commit()
            return {"user_id": user.id, "plan": user.plan, "status": user.status}
