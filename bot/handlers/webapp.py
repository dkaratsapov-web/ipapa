"""Связка с мини-аппом: кнопки открытия и подписки, пришедшие из приложения.

Мини-апп статический и своего сервера не имеет, поэтому:
- текущие подписки передаются ему в адресе (`?subs=1,2,3`), бот обновляет адрес
  кнопок после каждого изменения;
- изменения приходят в бот через `sendData` (запуск с кнопки клавиатуры) или
  через deep link `/start s<ID>` / `/start u<ID>` (запуск из меню).
"""
from __future__ import annotations

import json
import logging
import re
from html import escape
from urllib.parse import urlencode

from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import (KeyboardButton, MenuButtonWebApp, Message, ReplyKeyboardMarkup,
                           WebAppInfo)

from bot.formatting import item_title
from config import Config
from db.repo import Repo

log = logging.getLogger(__name__)
# /start s1_2-u3 — подписаться на 1 и 2, отписаться от 3; /start p5 — открыть товар 5
DEEP_LINK = re.compile(r"^[su]\d+(_\d+)*(-[su]\d+(_\d+)*)*$")
PRODUCT_LINK = re.compile(r"^p(\d+)$")


def parse_batch(payload: str) -> tuple[list[int], list[int]]:
    sub: list[int] = []
    unsub: list[int] = []
    for segment in payload.split("-"):
        target = sub if segment[0] == "s" else unsub
        target.extend(int(x) for x in segment[1:].split("_") if x)
    return sub, unsub
OPEN_TEXT = "🛍 Открыть магазин"


async def app_url(bot: Bot, config: Config, repo: Repo, tg_id: int, mode: str = "",
                  product_id: int = 0) -> str:
    me = await bot.me()
    subs = sorted(await repo.subscribed_ids(tg_id))
    params = {"bot": me.username or "", "subs": ",".join(map(str, subs))}
    if mode:
        params["m"] = mode
    if product_id:
        params["p"] = str(product_id)
    sep = "&" if "?" in config.miniapp_url else "?"
    return f"{config.miniapp_url}{sep}{urlencode(params)}"


async def app_keyboard(bot: Bot, config: Config, repo: Repo, tg_id: int) -> ReplyKeyboardMarkup:
    url = await app_url(bot, config, repo, tg_id, mode="kb")
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=OPEN_TEXT, web_app=WebAppInfo(url=url))]],
        resize_keyboard=True, is_persistent=True,
    )


async def refresh_menu_button(bot: Bot, config: Config, repo: Repo, tg_id: int) -> None:
    """Кнопка «Магазин» у поля ввода с актуальными подписками пользователя."""
    if not config.miniapp_url:
        return
    try:
        url = await app_url(bot, config, repo, tg_id)
        await bot.set_chat_menu_button(
            chat_id=tg_id, menu_button=MenuButtonWebApp(text="Магазин", web_app=WebAppInfo(url=url)))
    except Exception as exc:  # noqa: BLE001 — не критично
        log.warning("Не удалось обновить кнопку меню для %s: %s", tg_id, exc)


async def offer_app(message: Message, bot: Bot, config: Config, repo: Repo) -> None:
    if not config.miniapp_url:
        return
    await refresh_menu_button(bot, config, repo, message.chat.id)
    await message.answer("✨ Весь каталог в удобном приложении — кнопка внизу 👇",
                         reply_markup=await app_keyboard(bot, config, repo, message.chat.id))


async def _title(repo: Repo, product_id: int) -> str | None:
    product = await repo.get_product(product_id)
    if not product:
        return None
    if product["parent_id"]:
        parent = await repo.get_product(product["parent_id"])
        return item_title({**dict(product), "parent_name": parent["name"] if parent else None})
    return product["name"]


async def apply_batch(repo: Repo, tg_id: int, sub: list[int], unsub: list[int]) -> str:
    added, removed = [], []
    for pid in dict.fromkeys(sub):
        title = await _title(repo, pid)
        if title:
            await repo.add_subscription(tg_id, pid)
            added.append(title)
    for pid in dict.fromkeys(unsub):
        await repo.remove_subscription_by_product(tg_id, pid)
        title = await _title(repo, pid)
        removed.append(title or f"товар #{pid}")
    lines = []
    if added:
        lines.append("🔔 <b>Слежу за ценой:</b>")
        lines += [f"• {escape(t)}" for t in added]
        lines.append("Напишу, когда цена изменится или товар появится в наличии.")
    if removed:
        if lines:
            lines.append("")
        lines.append("🔕 <b>Больше не слежу:</b>")
        lines += [f"• {escape(t)}" for t in removed]
    return "\n".join(lines) or "Товар не найден — возможно, он снят с продажи."


async def reply_with_app(message: Message, bot: Bot, config: Config, repo: Repo, text: str) -> None:
    await refresh_menu_button(bot, config, repo, message.chat.id)
    markup = await app_keyboard(bot, config, repo, message.chat.id) if config.miniapp_url else None
    await message.answer(text, reply_markup=markup)


async def on_deep_link(message: Message, command: CommandObject, bot: Bot,
                       config: Config, repo: Repo) -> None:
    payload = command.args or ""
    from bot.handlers.leads import lead_from_deep_link
    if await lead_from_deep_link(message, bot, config, repo, payload):
        return
    if DEEP_LINK.match(payload):
        sub, unsub = parse_batch(payload)
        await reply_with_app(message, bot, config, repo, await apply_batch(repo, message.chat.id, sub, unsub))
        return
    from bot.handlers.user import cmd_start, render_product
    product = PRODUCT_LINK.match(payload)
    if product:
        await render_product(message, repo, config, int(product[1]))
        return
    await cmd_start(message, bot, config, repo)  # неизвестный параметр — обычное приветствие


async def on_web_app_data(message: Message, bot: Bot, config: Config, repo: Repo) -> None:
    """{"a": "batch", "sub": [..], "unsub": [..]}, {"a": "sub"|"unsub", "id": N} или {"a": "lead", ...}."""
    try:
        data = json.loads(message.web_app_data.data)
        if isinstance(data, dict) and data.get("ev"):
            from services.stats import log_app_batch
            await log_app_batch(repo.conn, message.from_user.id, data.get("ev"))
        if data.get("a") == "lead":
            from bot.handlers.leads import accept_lead
            from services.leads import from_web_app
            lead = from_web_app(data)
            if lead:
                await accept_lead(message, bot, config, repo, lead)
            else:
                log.warning("Некорректная заявка из мини-аппа: %r", message.web_app_data.data)
            return
        if data["a"] == "batch":
            sub = [int(x) for x in data.get("sub", [])][:200]
            unsub = [int(x) for x in data.get("unsub", [])][:200]
        else:
            ids = [int(data["id"])]
            sub, unsub = (ids, []) if data["a"] == "sub" else (([], ids) if data["a"] == "unsub" else ([], []))
    except (ValueError, KeyError, TypeError):
        log.warning("Некорректные данные из мини-аппа: %r", message.web_app_data.data)
        return
    if not sub and not unsub:
        return
    await reply_with_app(message, bot, config, repo, await apply_batch(repo, message.chat.id, sub, unsub))


def build_router() -> Router:
    router = Router(name="webapp")
    router.message.register(on_deep_link, CommandStart(deep_link=True))
    router.message.register(on_web_app_data, F.web_app_data)
    return router
