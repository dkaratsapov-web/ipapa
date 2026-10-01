"""Пользовательская часть: меню, каталог, поиск, карточка, подписки."""
from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, LinkPreviewOptions, Message

from bot import keyboards as kb
from bot.handlers.webapp import app_url, offer_app, refresh_menu_button
from bot.formatting import product_card
from config import Config
from db.repo import Repo
from services.parsing import search_terms
from services.specs_format import humanize
from services.stats import log_event

log = logging.getLogger(__name__)

WELCOME = (
    "👋 Привет! Я показываю актуальные цены и наличие в магазине "
    "<b>айпапа.рф</b> и сообщаю об изменениях цен.\n\n"
    "Выберите раздел или просто напишите, что ищете, например: <i>iphone 17 pro 256</i>"
)
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)


async def show(target: Message | CallbackQuery, text: str,
               markup: InlineKeyboardMarkup | None = None,
               preview: LinkPreviewOptions = NO_PREVIEW) -> None:
    """Редактирует сообщение при нажатии кнопки, иначе отправляет новое."""
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=markup, link_preview_options=preview)
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc):
                # Сообщение слишком старое или не текстовое — отправим новое
                await target.message.answer(text, reply_markup=markup, link_preview_options=preview)
        await target.answer()
    else:
        await target.answer(text, reply_markup=markup, link_preview_options=preview)


# ---------- меню ----------

async def main_menu(bot: Bot, config: Config, repo: Repo, tg_id: int) -> InlineKeyboardMarkup:
    url = await app_url(bot, config, repo, tg_id) if config.miniapp_url else ""
    return kb.main_menu(url)


async def cmd_start(message: Message, bot: Bot, config: Config, repo: Repo) -> None:
    await log_event(repo.conn, message.from_user.id, "start")
    await message.answer(WELCOME, reply_markup=await main_menu(bot, config, repo, message.chat.id))
    await offer_app(message, bot, config, repo)


async def cmd_menu(message: Message, bot: Bot, config: Config, repo: Repo) -> None:
    await message.answer(WELCOME, reply_markup=await main_menu(bot, config, repo, message.chat.id))


async def cb_main(call: CallbackQuery, bot: Bot, config: Config, repo: Repo) -> None:
    await show(call, WELCOME, await main_menu(bot, config, repo, call.from_user.id))


async def cb_search(call: CallbackQuery) -> None:
    await show(call, "🔎 Напишите название товара, например: <i>iphone 17 pro 256</i>",
               kb.back_to_menu())


async def cb_noop(call: CallbackQuery) -> None:
    await call.answer()


# ---------- каталог ----------

async def cb_catalog(call: CallbackQuery, repo: Repo) -> None:
    cats = await repo.top_categories()
    if not cats:
        await show(call, "Каталог ещё загружается, попробуйте через минуту.", kb.back_to_menu())
        return
    await show(call, "📱 <b>Каталог</b>\nВыберите категорию:", kb.categories_kb(cats))


async def cb_category(call: CallbackQuery, callback_data: kb.CatCb, repo: Repo) -> None:
    cat = await repo.get_category(callback_data.id)
    if not cat:
        await call.answer("Категория не найдена", show_alert=True)
        return
    if callback_data.page < 0:
        children = await repo.child_categories(cat["id"])
        if children:
            await show(call, f"📂 <b>{escape(cat['name'])}</b>",
                       kb.categories_kb(children, cat["id"], cat["parent_id"] or None))
            return
    page = max(callback_data.page, 0)
    rows, total = await repo.category_products(cat["id"], page * kb.PAGE_SIZE, kb.PAGE_SIZE)
    if not rows and page:
        page = 0
        rows, total = await repo.category_products(cat["id"], 0, kb.PAGE_SIZE)
    title = f"📂 <b>{escape(cat['name'])}</b>"
    text = f"{title} — товаров: {total}" if total else f"{title}\nТоваров нет."
    await show(call, text, kb.products_kb(rows, cat["id"], page, total, cat["parent_id"]))


# ---------- карточка товара ----------

async def render_product(target: Message | CallbackQuery, repo: Repo, config: Config,
                         product_id: int, cat: int = 0, page: int = 0) -> None:
    product = await repo.get_product(product_id)
    if product and product["type"] == "variation":  # открываем родителя
        product = await repo.get_product(product["parent_id"])
    if not product:
        if isinstance(target, CallbackQuery):
            await target.answer("Товар не найден", show_alert=True)
        return
    variations = await repo.get_variations(product["id"]) if product["type"] == "variable" else []
    specs, specs_url = await repo.specs_for_product(product) or ([], "")
    specs = humanize(specs, product["name"])
    text = product_card(product, variations, await repo.last_update_time(), config.tz,
                        specs=specs, specs_url=specs_url)
    image = product["image_url"] or next((v["image_url"] for v in variations if v["image_url"]), "")
    preview = (LinkPreviewOptions(url=image, prefer_large_media=True, show_above_text=True)
               if image else NO_PREVIEW)
    user_id = target.from_user.id
    await log_event(repo.conn, user_id, "bot_view", product["id"])
    subs = await repo.subscribed_ids(user_id)
    subscribed = product["id"] in subs or any(v["id"] in subs for v in variations)
    url = ""
    if config.miniapp_url:
        url = await app_url(target.bot, config, repo, user_id, product_id=product["id"])
    await show(target, text, kb.product_kb(product["id"], cat, page, subscribed, url), preview)


async def cb_product(call: CallbackQuery, callback_data: kb.ProdCb, repo: Repo, config: Config) -> None:
    await render_product(call, repo, config, callback_data.id, callback_data.cat, callback_data.page)


# ---------- подписки ----------

async def cb_sub_menu(call: CallbackQuery, callback_data: kb.SubMenuCb, repo: Repo) -> None:
    product = await repo.get_product(callback_data.pid)
    if not product:
        await call.answer("Товар не найден", show_alert=True)
        return
    variations = await repo.get_variations(product["id"]) if product["type"] == "variable" else []
    subs = await repo.subscribed_ids(call.from_user.id)
    text = (f"🔔 <b>{escape(product['name'])}</b>\n\nНа что подписаться? Я пришлю сообщение, "
            "когда изменится цена или товар появится в наличии.\nПовторное нажатие — отписка.")
    await show(call, text, kb.subscribe_kb(product, variations, subs, callback_data.page))


async def cb_sub_toggle(call: CallbackQuery, callback_data: kb.SubAddCb, repo: Repo,
                        bot: Bot, config: Config) -> None:
    user_id = call.from_user.id
    if callback_data.id in await repo.subscribed_ids(user_id):
        await repo.remove_subscription_by_product(user_id, callback_data.id)
        note = "Подписка отменена"
    else:
        await repo.add_subscription(user_id, callback_data.id)
        note = "✅ Подписка оформлена"
    await refresh_menu_button(bot, config, repo, user_id)
    product = await repo.get_product(callback_data.pid)
    if not product:
        await call.answer(note)
        return
    variations = await repo.get_variations(product["id"]) if product["type"] == "variable" else []
    page = next((i // kb.PAGE_SIZE for i, v in enumerate(variations) if v["id"] == callback_data.id), 0)
    subs = await repo.subscribed_ids(user_id)
    try:
        await call.message.edit_reply_markup(
            reply_markup=kb.subscribe_kb(product, variations, subs, page))
    except TelegramBadRequest:
        pass
    await call.answer(note)


async def render_subscriptions(target: Message | CallbackQuery, repo: Repo) -> None:
    subs = await repo.user_subscriptions(target.from_user.id)
    if not subs:
        text = "У вас пока нет подписок. Откройте товар и нажмите «🔔 Следить за ценой»."
    else:
        text = f"🔔 <b>Мои подписки</b> ({len(subs)})\nНажмите ❌, чтобы отписаться."
    await show(target, text, kb.subscriptions_kb(subs))


async def cb_subs(call: CallbackQuery, repo: Repo) -> None:
    await render_subscriptions(call, repo)


async def cmd_subs(message: Message, repo: Repo) -> None:
    await render_subscriptions(message, repo)


async def cb_unsub(call: CallbackQuery, callback_data: kb.UnsubCb, repo: Repo,
                   bot: Bot, config: Config) -> None:
    await repo.remove_subscription(call.from_user.id, callback_data.sub_id)
    await refresh_menu_button(bot, config, repo, call.from_user.id)
    await render_subscriptions(call, repo)


# ---------- поиск (любой текст) ----------

async def on_search(message: Message, repo: Repo) -> None:
    await log_event(repo.conn, message.from_user.id, "bot_search", value=message.text)
    terms = search_terms(message.text)
    rows = await repo.search(terms, limit=kb.PAGE_SIZE + 1)
    if not rows:
        await message.answer("Ничего не нашлось 😕 Попробуйте иначе, например: <i>iphone 17 pro</i>",
                             reply_markup=kb.back_to_menu())
        return
    more = len(rows) > kb.PAGE_SIZE
    text = "🔎 Нашлось больше 10 товаров, показаны первые 10 — уточните запрос." if more \
        else f"🔎 Найдено: {len(rows)}"
    await message.answer(text, reply_markup=kb.search_results_kb(rows[:kb.PAGE_SIZE]))


def build_router() -> Router:
    router = Router(name="user")
    router.message.register(cmd_start, CommandStart())
    router.message.register(cmd_menu, Command("menu"))
    router.callback_query.register(cb_main, kb.MenuCb.filter(F.action == "main"))
    router.callback_query.register(cb_search, kb.MenuCb.filter(F.action == "search"))
    router.callback_query.register(cb_noop, kb.NoopCb.filter())
    router.callback_query.register(cb_catalog, kb.MenuCb.filter(F.action == "catalog"))
    router.callback_query.register(cb_category, kb.CatCb.filter())
    router.callback_query.register(cb_product, kb.ProdCb.filter())
    router.callback_query.register(cb_sub_menu, kb.SubMenuCb.filter())
    router.callback_query.register(cb_sub_toggle, kb.SubAddCb.filter())
    router.callback_query.register(cb_subs, kb.MenuCb.filter(F.action == "subs"))
    router.message.register(cmd_subs, Command("subs"))
    router.callback_query.register(cb_unsub, kb.UnsubCb.filter())
    # Любой текст — поиск; регистрируется последним
    router.message.register(on_search, F.text & ~F.text.startswith("/"))
    return router
