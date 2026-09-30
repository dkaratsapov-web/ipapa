"""Команды администратора: /sync, /changes, /stats, /digest."""
from __future__ import annotations

from html import escape

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import LinkPreviewOptions, Message

from bot.formatting import fmt_dt, sync_summary
from config import Config
from db.repo import Repo
from services.jobs import Jobs
from services.reports import changes_report, daily_digest

NO_PREVIEW = LinkPreviewOptions(is_disabled=True)
ADMIN_HELP = (
    "<b>Команды администратора</b>\n"
    "/sync — синхронизировать сейчас\n"
    "/changes [N] — изменения цен за N часов (по умолчанию 24)\n"
    "/stats — статистика\n"
    "/digest — прислать ежедневную сводку сейчас\n"
    "/leads — последние заявки из мини-аппа"
)


def build_router(admin_ids: frozenset[int]) -> Router:
    router = Router(name="admin")
    router.message.filter(lambda m: m.from_user is not None and m.from_user.id in admin_ids)

    @router.message(Command("admin"))
    async def cmd_admin(message: Message) -> None:
        await message.answer(ADMIN_HELP)

    @router.message(Command("sync"))
    async def cmd_sync(message: Message, jobs: Jobs, config: Config) -> None:
        if jobs.sync.running:
            await message.answer("⏳ Синхронизация уже выполняется, дождитесь окончания.")
            return
        await message.answer("⏳ Запускаю синхронизацию…")
        result = await jobs.sync_and_notify(alert_admins=False)
        text = sync_summary(result, config.tz)
        if result.ok and result.changes:
            text += "\nПодробнее: /changes 1"
        await message.answer(text)

    @router.message(Command("changes"))
    async def cmd_changes(message: Message, command: CommandObject, repo: Repo, config: Config) -> None:
        hours = 24.0
        if command.args:
            try:
                hours = float(command.args.strip().replace(",", "."))
            except ValueError:
                await message.answer("Использование: /changes [часы], например /changes 6")
                return
            if not 0 < hours <= 24 * 90:
                await message.answer("Укажите число часов от 1 до 2160.")
                return
        for text in await changes_report(repo, hours, config.tz):
            await message.answer(text, link_preview_options=NO_PREVIEW)

    @router.message(Command("stats"))
    async def cmd_stats(message: Message, repo: Repo, config: Config) -> None:
        users, active = await repo.count_users()
        subs = await repo.count_subscriptions()
        products, variations = await repo.product_counts()
        ok = await repo.last_sync("success")
        last = await repo.last_sync()
        lines = [
            "📊 <b>Статистика</b>",
            f"Пользователей: {users} (активных {active})",
            f"Подписок: {subs}",
            f"Товаров в базе: {products}, вариантов: {variations}",
            f"Последняя успешная синхронизация: {fmt_dt(ok['finished_at'] if ok else None, config.tz)}",
        ]
        if last and last["status"] == "failed":
            lines.append(f"⚠️ Последняя попытка {fmt_dt(last['finished_at'], config.tz)} "
                         f"завершилась ошибкой: {escape(last['error'] or '')}")
        lines.append(f"Интервал синхронизации: {config.sync_interval_min} мин, "
                     f"сводка в {config.digest_time.strftime('%H:%M')}")
        await message.answer("\n".join(lines))

    @router.message(Command("digest"))
    async def cmd_digest(message: Message, repo: Repo, config: Config) -> None:
        for text in await daily_digest(repo, config.tz):
            await message.answer(text, link_preview_options=NO_PREVIEW)

    return router
