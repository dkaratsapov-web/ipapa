"""Middleware: регистрация пользователей в БД."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from db.repo import Repo


class UserMiddleware(BaseMiddleware):
    def __init__(self, repo: Repo, admin_ids: frozenset[int]):
        self.repo = repo
        self.admin_ids = admin_ids
        self._seen: set[int] = set()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        # Запись раз за запуск + при каждом /start (снимает флаг неактивности)
        if user and not user.is_bot:
            message = getattr(event, "message", None)
            is_start = bool(message and message.text and message.text.startswith("/start"))
            if user.id not in self._seen or is_start:
                await self.repo.upsert_user(user.id, user.username, user.id in self.admin_ids)
                self._seen.add(user.id)
        return await handler(event, data)
