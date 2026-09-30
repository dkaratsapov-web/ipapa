"""Тексты сообщений (HTML parse mode)."""
from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from db.database import parse_ts
from services.parsing import format_diff, format_price, short_label

MAX_TEXT = 4000  # запас до лимита Telegram 4096


def fmt_dt(iso: str | None, tz: ZoneInfo) -> str:
    if not iso:
        return "—"
    return parse_ts(iso).astimezone(tz).strftime("%d.%m.%Y %H:%M")


def item_title(row: Mapping[str, Any]) -> str:
    """«iPhone 17 Pro 256 ГБ · Silver» для варианта, название — для товара."""
    parent_name = row["parent_name"] if "parent_name" in row.keys() else None
    base = parent_name or row["name"]
    label = short_label(row["variation_label"] or "")
    return f"{base} {label}".strip() if label else base


def price_html(price: int, regular: int) -> str:
    if price and regular and regular > price:
        return f"<s>{format_price(regular)}</s> <b>{format_price(price)}</b>"
    return f"<b>{format_price(price)}</b>" if price else format_price(0)


def product_card(product: Mapping[str, Any], variations: list[Mapping[str, Any]],
                 updated_at: str | None, tz: ZoneInfo) -> str:
    head = [f"<b>{escape(product['name'])}</b>"]
    if product["permalink"]:
        head.append(f'<a href="{escape(product["permalink"])}">Открыть на сайте</a>')
    head.append("")

    lines: list[str] = []
    if variations:
        for v in variations:
            mark = "✅" if v["in_stock"] else "❌"
            label = escape(short_label(v["variation_label"]) or v["name"])
            lines.append(f"{mark} {label} — {price_html(v['price'], v['regular_price'])}")
    else:
        mark = "✅ в наличии" if product["in_stock"] else "❌ нет в наличии"
        lines.append(f"{price_html(product['price'], product['regular_price'])} · {mark}")

    tail = ["", f"<i>Обновлено: {fmt_dt(updated_at, tz)}</i>"]
    text = "\n".join(head + lines + tail)
    if len(text) > MAX_TEXT:  # обрезаем список вариантов
        budget = MAX_TEXT - len("\n".join(head + tail)) - 60
        kept, size = [], 0
        for line in lines:
            if size + len(line) + 1 > budget:
                break
            kept.append(line)
            size += len(line) + 1
        kept.append(f"… и ещё {len(lines) - len(kept)} вариантов — см. на сайте")
        text = "\n".join(head + kept + tail)
    return text


def product_list_line(row: Mapping[str, Any]) -> str:
    """Подпись кнопки в списке товаров."""
    stock = "" if row["any_stock"] else "❌ "
    price = format_price(row["min_price"])
    prefix = "от " if row["type"] == "variable" and row["min_price"] else ""
    return f"{stock}{row['name']} — {prefix}{price}"


def change_line(ev: Mapping[str, Any], with_link: bool = True) -> str:
    title = escape(item_title(ev))
    link = ev["permalink"] or (ev["parent_permalink"] if "parent_permalink" in ev.keys() else "")
    if with_link and link:
        title = f'<a href="{escape(link)}">{title}</a>'
    old, new = ev["old_price"], ev["new_price"]
    parts = []
    if old > 0 and new > 0 and old != new:
        parts.append(f"{format_price(old)} → <b>{format_price(new)}</b> ({format_diff(new - old)})")
    if ev["old_in_stock"] != ev["new_in_stock"]:
        parts.append("✅ появился в наличии" if ev["new_in_stock"] else "❌ нет в наличии")
    return f"{title}: " + ", ".join(parts)


def notification_text(ev: Mapping[str, Any]) -> str:
    return "🔔 " + change_line(ev)


def split_messages(lines: list[str], header: str = "") -> list[str]:
    """Режет длинный список строк на сообщения под лимит Telegram."""
    messages, current = [], header
    for line in lines:
        if len(current) + len(line) + 1 > MAX_TEXT:
            messages.append(current)
            current = ""
        current = f"{current}\n{line}" if current else line
    if current:
        messages.append(current)
    return messages


def sync_summary(result: Any, tz: ZoneInfo) -> str:
    if not result.ok:
        return f"❌ <b>Синхронизация не удалась</b>\n{escape(result.error or '')}\nБаза не изменена."
    lines = [
        "✅ <b>Синхронизация завершена</b>",
        f"Товаров: {result.products_count} (X-WP-Total: {result.products_total})",
        f"Вариантов: {result.variations_count} (X-WP-Total: {result.variations_total})",
        f"Категорий: {result.categories_count}",
        f"Изменений цен: {result.price_changes}",
        f"Изменений наличия: {result.stock_changes}",
    ]
    if result.new_items:
        lines.append(f"Новых позиций: {result.new_items}")
    if result.deactivated:
        lines.append(f"Снято с сайта: {result.deactivated}")
    if result.first_sync:
        lines.append("Первая синхронизация — уведомления не рассылаются.")
    lines.append(f"Время: {result.duration:.1f} с · {datetime.now(tz).strftime('%d.%m.%Y %H:%M')}")
    return "\n".join(lines)
