"""Точка входа: Telegram-бот цен магазина айпапа.рф."""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeChat
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from bot.handlers import admin, user
from bot.middlewares import UserMiddleware
from config import Config, load_config
from db.database import connect
from db.repo import Repo
from services.api_client import StoreApiClient
from services.jobs import Jobs
from services.notifier import Notifier
from services.sync import SyncService


def setup_logging(log_path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(fmt)
    file = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=[stdout, file])
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


async def set_commands(bot: Bot, config: Config) -> None:
    user_cmds = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="subs", description="Мои подписки"),
    ]
    await bot.set_my_commands(user_cmds)
    admin_cmds = user_cmds + [
        BotCommand(command="sync", description="Синхронизировать сейчас"),
        BotCommand(command="changes", description="Изменения цен за N часов"),
        BotCommand(command="stats", description="Статистика"),
        BotCommand(command="digest", description="Сводка сейчас"),
    ]
    for admin_id in config.admin_ids:
        try:
            await bot.set_my_commands(admin_cmds, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as exc:  # noqa: BLE001 — админ мог ещё не писать боту
            logging.warning("Не удалось задать команды для админа %s: %s", admin_id, exc)


async def main() -> None:
    config = load_config()
    setup_logging(config.log_path)
    log = logging.getLogger("main")

    conn = await connect(config.db_path)
    repo = Repo(conn)
    client = StoreApiClient(config.site_api_url)
    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    notifier = Notifier(bot, repo)
    jobs = Jobs(config, repo, SyncService(conn, client), notifier)

    dp = Dispatcher(repo=repo, config=config, jobs=jobs)
    dp.update.outer_middleware(UserMiddleware(repo, config.admin_ids))
    dp.include_router(admin.build_router(config.admin_ids))
    dp.include_router(user.build_router())  # последним: ловит любой текст как поиск

    scheduler = AsyncIOScheduler(timezone=config.tz)
    scheduler.add_job(
        jobs.scheduled_sync, IntervalTrigger(minutes=config.sync_interval_min),
        next_run_time=datetime.now(config.tz),  # сразу при старте
        id="sync", max_instances=1, coalesce=True,
    )
    scheduler.add_job(
        jobs.send_digest,
        CronTrigger(hour=config.digest_time.hour, minute=config.digest_time.minute),
        id="digest", misfire_grace_time=3600, coalesce=True,
    )
    scheduler.start()

    log.info("Бот запущен: синхронизация каждые %d мин, сводка в %s (%s)",
             config.sync_interval_min, config.digest_time.strftime("%H:%M"), config.tz_name)
    try:
        await set_commands(bot, config)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await client.close()
        await conn.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
