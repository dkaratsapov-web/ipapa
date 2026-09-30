"""Фоновые задачи: синхронизация по расписанию и ежедневная сводка."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from bot.formatting import sync_summary
from config import Config
from db.repo import Repo
from services.export import export_catalog, run_publish_cmd
from services import tradein
from services.images import ImageMatcher
from services.notifier import Notifier
from services.reports import daily_digest
from services.specs import SpecsMatcher
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
            await tradein.refresh(self.repo.conn, self.sync.client, self.config.site_url)
            await self.match_images()
            await self.export()
            # характеристики ищутся долго (1 запрос/с) — каталог уже выгружен, перевыгружаем при находках
            if await self.match_specs():
                await self.export()
        elif alert_admins:
            await self.notifier.to_admins(self.config.admin_ids,
                                          "⚠️ " + sync_summary(result, self.config.tz))
        return result

    async def match_images(self) -> None:
        matcher = ImageMatcher(self.repo.conn)
        try:
            found = await matcher.run()
            if found:
                log.info("Подобрано картинок: %d", found)
        except Exception:  # noqa: BLE001 — подбор картинок не должен ломать синхронизацию
            log.exception("Ошибка подбора картинок")
        finally:
            await matcher.close()

    async def match_specs(self) -> int:
        matcher = SpecsMatcher(self.repo.conn)
        try:
            found = await matcher.run()
            if found:
                log.info("Найдено характеристик моделей: %d", found)
            return found
        except Exception:  # noqa: BLE001 — подбор характеристик не должен ломать синхронизацию
            log.exception("Ошибка подбора характеристик")
            return 0
        finally:
            await matcher.close()

    async def export(self) -> None:
        if not self.config.export_path:
            return
        try:
            await export_catalog(self.repo.conn, self.config.export_path)
            if self.config.export_cmd:
                await run_publish_cmd(self.config.export_cmd)
        except Exception:  # noqa: BLE001 — сбой выгрузки не должен ломать синхронизацию
            log.exception("Ошибка выгрузки каталога")

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
