"""Заявки из мини-аппа: сохранить, переслать менеджерам, попросить телефон."""
from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, User

from bot.formatting import fmt_dt
from config import Config
from db.repo import Repo
from services import leads, tradein

log = logging.getLogger(__name__)

CONTACT_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📞 Отправить номер телефона", request_contact=True)]],
    resize_keyboard=True, one_time_keyboard=True,
)


def _who(user: User, phone: str) -> str:
    name = escape(user.full_name or "")
    link = f'<a href="tg://user?id={user.id}">{name or user.id}</a>'
    parts = [link]
    if user.username:
        parts.append(f"@{escape(user.username)}")
    if phone:
        parts.append(f"📞 {escape(phone)}")
    return " · ".join(parts)


async def notify_managers(bot: Bot, config: Config, text: str) -> None:
    for chat_id in config.lead_recipients:
        try:
            await bot.send_message(chat_id, text, disable_web_page_preview=True)
        except Exception as exc:  # noqa: BLE001 — одна недоступная точка не должна терять заявку
            log.warning("Заявка не доставлена в %s: %s", chat_id, exc)


async def accept_lead(message: Message, bot: Bot, config: Config, repo: Repo, lead: leads.Lead) -> None:
    user = message.from_user
    lead_id = await leads.save(repo.conn, user.id, user.username, lead)
    body = await leads.describe(repo.conn, lead)
    title = leads.KINDS[lead.kind]
    name = lead.data.get("name")
    await notify_managers(
        bot, config,
        f"{title} <b>№{lead_id}</b>\n{body}\n\nКлиент: {escape(name) + ' · ' if name else ''}{_who(user, lead.phone)}",
    )
    reply = f"✅ <b>Заявка №{lead_id} принята</b> — {title[2:].lower()}\n{body}\n\n"
    if lead.phone:
        reply += "Менеджер свяжется с вами в ближайшее время."
        from bot.handlers.webapp import app_keyboard
        markup = await app_keyboard(bot, config, repo, message.chat.id) if config.miniapp_url else None
    else:
        reply += "Оставьте номер телефона — менеджер перезвонит. Или просто дождитесь сообщения здесь."
        markup = CONTACT_KB
    await message.answer(reply, reply_markup=markup)
    log.info("Заявка №%d (%s) от %s", lead_id, lead.kind, user.id)


async def on_contact(message: Message, bot: Bot, config: Config, repo: Repo) -> None:
    contact = message.contact
    if contact.user_id and contact.user_id != message.from_user.id:
        await message.answer("Отправьте, пожалуйста, свой номер кнопкой ниже.", reply_markup=CONTACT_KB)
        return
    phone = leads.clean_phone(contact.phone_number)
    lead_id = await leads.set_phone(repo.conn, message.from_user.id, phone) if phone else None
    from bot.handlers.webapp import app_keyboard
    markup = await app_keyboard(bot, config, repo, message.chat.id) if config.miniapp_url else None
    if not lead_id:
        await message.answer("Спасибо! Открытых заявок нет — оформите заказ или заявку в приложении.",
                             reply_markup=markup)
        return
    await notify_managers(bot, config, f"📞 Телефон к заявке <b>№{lead_id}</b>: {_who(message.from_user, phone)}")
    await message.answer(f"Спасибо! Телефон добавлен к заявке №{lead_id}, скоро перезвоним.", reply_markup=markup)


async def lead_from_deep_link(message: Message, bot: Bot, config: Config, repo: Repo, payload: str) -> bool:
    """True — payload оказался заявкой и обработан."""
    lead = leads.from_deep_link(payload, await tradein.load(repo.conn))
    if not lead:
        return False
    await accept_lead(message, bot, config, repo, lead)
    return True


def build_admin_router(admin_ids: frozenset[int]) -> Router:
    router = Router(name="leads-admin")
    router.message.filter(lambda m: m.from_user is not None and m.from_user.id in admin_ids)

    @router.message(Command("leads"))
    async def cmd_leads(message: Message, repo: Repo, config: Config) -> None:
        rows = await leads.recent(repo.conn, 10)
        if not rows:
            await message.answer("Заявок пока нет.")
            return
        lines = ["<b>Последние заявки</b>"]
        for r in rows:
            who = f"@{escape(r['username'])}" if r["username"] else f"id {r['tg_id']}"
            phone = f" · {escape(r['phone'])}" if r["phone"] else ""
            lines.append(f"№{r['id']} {leads.KINDS.get(r['kind'], r['kind'])} · {fmt_dt(r['created_at'], config.tz)} · {who}{phone}")
        await message.answer("\n".join(lines))

    return router


def build_router() -> Router:
    router = Router(name="leads")
    router.message.register(on_contact, F.contact)
    return router
