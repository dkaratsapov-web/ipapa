"""Inline-клавиатуры и callback data."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.formatting import item_title, product_list_line
from services.parsing import format_price, short_label

PAGE_SIZE = 10


class MenuCb(CallbackData, prefix="m"):
    action: str  # main / catalog / search / subs


class CatCb(CallbackData, prefix="c"):
    id: int
    page: int = 0


class ProdCb(CallbackData, prefix="p"):
    id: int
    cat: int = 0   # откуда пришли: категория (0 — из поиска/подписок)
    page: int = 0


class SubMenuCb(CallbackData, prefix="sm"):
    pid: int
    page: int = 0


class SubAddCb(CallbackData, prefix="sa"):
    id: int    # товар (все варианты) или конкретный вариант
    pid: int   # карточка, в которую вернуться


class UnsubCb(CallbackData, prefix="u"):
    sub_id: int


class NoopCb(CallbackData, prefix="n"):
    pass


def _cut(text: str, limit: int = 60) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def main_menu(app_url: str = "") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if app_url:
        kb.button(text="🛍 Открыть магазин", web_app=WebAppInfo(url=app_url))
    kb.button(text="📱 Каталог", callback_data=MenuCb(action="catalog"))
    kb.button(text="🔎 Поиск", callback_data=MenuCb(action="search"))
    kb.button(text="🔔 Мои подписки", callback_data=MenuCb(action="subs"))
    kb.adjust(*([1] if app_url else []), 2, 1)
    return kb.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ В меню", callback_data=MenuCb(action="main").pack())
    ]])


def categories_kb(categories: Sequence[Mapping[str, Any]], parent_id: int = 0,
                  grand_parent: int | None = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if parent_id:
        kb.button(text="📋 Все товары раздела", callback_data=CatCb(id=parent_id, page=0))
    for c in categories:
        kb.button(text=_cut(f"{c['name']} ({c['count']})"), callback_data=CatCb(id=c["id"], page=-1))
    if parent_id:
        back = CatCb(id=grand_parent, page=-1) if grand_parent else MenuCb(action="catalog")
        kb.button(text="⬅️ Назад", callback_data=back)
    else:
        kb.button(text="⬅️ В меню", callback_data=MenuCb(action="main"))
    kb.adjust(*([1] if parent_id else []), 2)
    return kb.as_markup()


def _pager(kb: InlineKeyboardBuilder, page: int, total: int, make) -> None:
    pages = max(1, -(-total // PAGE_SIZE))
    if pages <= 1:
        return
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="◀️", callback_data=make(page - 1).pack()))
    row.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data=NoopCb().pack()))
    if page < pages - 1:
        row.append(InlineKeyboardButton(text="▶️", callback_data=make(page + 1).pack()))
    kb.row(*row)


def products_kb(rows: Sequence[Mapping[str, Any]], cat_id: int, page: int, total: int,
                back_parent: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for r in rows:
        kb.row(InlineKeyboardButton(text=_cut(product_list_line(r)),
                                    callback_data=ProdCb(id=r["id"], cat=cat_id, page=page).pack()))
    _pager(kb, page, total, lambda p: CatCb(id=cat_id, page=p))
    back = CatCb(id=back_parent, page=-1) if back_parent else MenuCb(action="catalog")
    kb.row(InlineKeyboardButton(text="⬅️ К категориям", callback_data=back.pack()))
    return kb.as_markup()


def search_results_kb(rows: Sequence[Mapping[str, Any]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for r in rows:
        kb.row(InlineKeyboardButton(text=_cut(product_list_line(r)),
                                    callback_data=ProdCb(id=r["id"]).pack()))
    kb.row(InlineKeyboardButton(text="⬅️ В меню", callback_data=MenuCb(action="main").pack()))
    return kb.as_markup()


def product_kb(product_id: int, cat: int, page: int, subscribed: bool,
               app_url: str = "") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if app_url:
        kb.button(text="🛍 Открыть в приложении", web_app=WebAppInfo(url=app_url))
    kb.button(text="🔔 Следить за ценой" + (" ✓" if subscribed else ""),
              callback_data=SubMenuCb(pid=product_id))
    if cat:
        kb.button(text="⬅️ К списку", callback_data=CatCb(id=cat, page=page))
    kb.button(text="🏠 Меню", callback_data=MenuCb(action="main"))
    kb.adjust(*([1] if app_url else []), 1, 2)
    return kb.as_markup()


def subscribe_kb(product: Mapping[str, Any], variations: Sequence[Mapping[str, Any]],
                 subscribed: set[int], page: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    mark = lambda pid: "✓ " if pid in subscribed else ""  # noqa: E731
    kb.row(InlineKeyboardButton(text=f"{mark(product['id'])}Все варианты",
                                callback_data=SubAddCb(id=product["id"], pid=product["id"]).pack()))
    chunk = variations[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    for v in chunk:
        label = short_label(v["variation_label"]) or v["name"]
        kb.row(InlineKeyboardButton(
            text=_cut(f"{mark(v['id'])}{label} — {format_price(v['price'])}"),
            callback_data=SubAddCb(id=v["id"], pid=product["id"]).pack()))
    _pager(kb, page, len(variations), lambda p: SubMenuCb(pid=product["id"], page=p))
    kb.row(InlineKeyboardButton(text="⬅️ К товару", callback_data=ProdCb(id=product["id"]).pack()))
    return kb.as_markup()


def subscriptions_kb(subs: Sequence[Mapping[str, Any]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in subs:
        title = item_title(s) if s["name"] else f"Товар #{s['product_id']}"
        open_id = (s["parent_id"] or s["product_id"]) if s["name"] else None
        row = []
        if open_id:
            row.append(InlineKeyboardButton(text=_cut(title, 40),
                                            callback_data=ProdCb(id=open_id).pack()))
        row.append(InlineKeyboardButton(text="❌ Отписаться" if not open_id else "❌",
                                        callback_data=UnsubCb(sub_id=s["sub_id"]).pack()))
        kb.row(*row)
    kb.row(InlineKeyboardButton(text="⬅️ В меню", callback_data=MenuCb(action="main").pack()))
    return kb.as_markup()
