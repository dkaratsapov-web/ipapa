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
DEEP_LINK = re.compile(r"^([su])(\d+)$")
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


async def apply_action(repo: Repo, tg_id: int, action: str, product_id: int) -> str:
    product = await repo.get_product(product_id)
    if not product:
        return "Товар не найден — возможно, он снят с продажи."
    title = product["name"]
    if product["parent_id"]:
        parent = await repo.get_product(product["parent_id"])
        title = item_title({**dict(product), "parent_name": parent["name"] if parent else None})
    if action == "s":
        await repo.add_subscription(tg_id, product_id)
        return f"🔔 Слежу за ценой: <b>{escape(title)}</b>\nНапишу, когда цена изменится или товар появится в наличии."
    await repo.remove_subscription_by_product(tg_id, product_id)
    return f"🔕 Больше не слежу: <b>{escape(title)}</b>"


async def on_deep_link(message: Message, command: CommandObject, bot: Bot,
                       config: Config, repo: Repo) -> None:
    match = DEEP_LINK.match(command.args or "")
    if not match:
        # неизвестный параметр — обычное приветствие
        from bot.handlers.user import cmd_start
        await cmd_start(message, bot, config, repo)
        return
    text = await apply_action(repo, message.chat.id, match[1], int(match[2]))
    await refresh_menu_button(bot, config, repo, message.chat.id)
    markup = await app_keyboard(bot, config, repo, message.chat.id) if config.miniapp_url else None
    await message.answer(text, reply_markup=markup)


async def on_web_app_data(message: Message, bot: Bot, config: Config, repo: Repo) -> None:
    try:
        data = json.loads(message.web_app_data.data)
        action = {"sub": "s", "unsub": "u"}[data["a"]]
        product_id = int(data["id"])
    except (ValueError, KeyError, TypeError):
        log.warning("Некорректные данные из мини-аппа: %r", message.web_app_data.data)
        return
    text = await apply_action(repo, message.chat.id, action, product_id)
    await refresh_menu_button(bot, config, repo, message.chat.id)
    await message.answer(text, reply_markup=await app_keyboard(bot, config, repo, message.chat.id))


def build_router() -> Router:
    router = Router(name="webapp")
    router.message.register(on_deep_link, CommandStart(deep_link=True))
    router.message.register(on_web_app_data, F.web_app_data)
    return router
