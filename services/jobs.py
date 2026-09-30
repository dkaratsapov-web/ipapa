"""Фоновые задачи: синхронизация по расписанию и ежедневная сводка."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from bot.formatting import sync_summary
from config import Config
from db.repo import Repo
from services.notifier import Notifier
from services.reports import daily_digest
from services.sync import SyncResult, SyncService

log = logging.getLogger(__name__)


@dataclass
class Jobs:
    config: Config
    repo: Repo
    sync: SyncService
    notifier: Notifier

    async def sync_and_notify(self, alert_admins: bool = True) -> SyncResult:
        result = await self.sync.run()
        if result.ok:
            await self.notifier.process_queue()
        elif alert_admins:
            await self.notifier.to_admins(self.config.admin_ids,
                                          "⚠️ " + sync_summary(result, self.config.tz))
        return result

    async def scheduled_sync(self) -> None:
        if self.sync.running:
            log.info("Синхронизация уже идёт — пропускаем запуск по расписанию")
            return
        try:
            await self.sync_and_notify()
        except Exception:  # noqa: BLE001 — планировщик не должен падать
            log.exception("Ошибка фоновой синхронизации")

    async def send_digest(self) -> None:
        try:
            texts = await daily_digest(self.repo, self.config.tz)
            await self.notifier.to_admins(self.config.admin_ids, texts)
        except Exception:  # noqa: BLE001
            log.exception("Ошибка отправки сводки")
