"""Рассылка уведомлений подписчикам и администраторам."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

from bot.formatting import notification_text
from db.repo import Repo

log = logging.getLogger(__name__)

SEND_DELAY = 0.05  # не менее 50 мс между сообщениями


class Notifier:
    def __init__(self, bot: Bot, repo: Repo, delay: float = SEND_DELAY):
        self.bot = bot
        self.repo = repo
        self.delay = delay
        self._lock = asyncio.Lock()

    async def send(self, chat_id: int, text: str, **kwargs) -> bool:
        """Отправка с обработкой flood-limit и блокировки бота."""
        for _ in range(3):
            try:
                await self.bot.send_message(chat_id, text, **kwargs)
                return True
            except TelegramRetryAfter as exc:
                log.warning("Flood limit, ждём %s с", exc.retry_after)
                await asyncio.sleep(exc.retry_after + 0.5)
            except TelegramForbiddenError:
                log.info("Пользователь %s заблокировал бота — помечаем неактивным", chat_id)
                await self.repo.mark_user_inactive(chat_id)
                return False
            except TelegramBadRequest as exc:
                if "chat not found" in str(exc).lower():
                    await self.repo.mark_user_inactive(chat_id)
                log.warning("Не удалось отправить %s: %s", chat_id, exc)
                return False
            finally:
                await asyncio.sleep(self.delay)
        return False

    async def process_queue(self) -> int:
        """Разослать уведомления по необработанным событиям price_history."""
        async with self._lock:
            events = await self.repo.pending_events()
            sent = 0
            for ev in events:
                notify = (
                    (ev["old_price"] > 0 and ev["new_price"] > 0 and ev["old_price"] != ev["new_price"])
                    or (not ev["old_in_stock"] and ev["new_in_stock"])
                )
                if notify:
                    text = notification_text(ev)
                    for tg_id in await self.repo.subscribers_for(ev["product_id"], ev["parent_id"]):
                        if await self.send(tg_id, text, disable_web_page_preview=True):
                            sent += 1
                await self.repo.mark_notified([ev["id"]])
            if sent:
                log.info("Отправлено уведомлений: %d", sent)
            return sent

    async def to_admins(self, admin_ids: frozenset[int], texts: str | list[str]) -> None:
        for text in [texts] if isinstance(texts, str) else texts:
            for admin in admin_ids:
                await self.send(admin, text, disable_web_page_preview=True)
