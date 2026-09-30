"""Разбор ответов WooCommerce Store API и форматирование цен."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any


def parse_price(value: Any, minor_unit: int = 2) -> int:
    """Цена из API (строка в минимальных единицах) -> целые копейки.

    При currency_minor_unit=2 "11470000" -> 11470000 коп. (114 700 ₽).
    При currency_minor_unit=0 "114700" -> 11470000 коп.
    Пустое значение -> 0 («цена по запросу»).
    """
    if value is None:
        return 0
    s = str(value).strip()
    if not s:
        return 0
    try:
        amount = int(s)
    except ValueError:
        amount = round(float(s))
    shift = 2 - int(minor_unit)
    if shift >= 0:
        return amount * 10**shift
    return round(amount / 10 ** (-shift))


def parse_variation_label(raw: Any) -> str:
    """Поле `variation` варианта -> строка «Память: 2 ТБ, Цвет: Silver, ...».

    Store API отдаёт строку; на всякий случай поддерживаем и список атрибутов.
    """
    if not raw:
        return ""
    if isinstance(raw, str):
        return html.unescape(raw).strip()
    if isinstance(raw, list):
        parts = []
        for item in raw:
            if isinstance(item, dict):
                name = item.get("attribute") or item.get("name") or ""
                val = item.get("value") or ""
                parts.append(f"{name}: {val}" if name else str(val))
        return ", ".join(p for p in parts if p)
    return str(raw)


def short_label(label: str) -> str:
    """«Память: 2 ТБ, Цвет: Silver, Количество сим-карт: eSIM» -> «2 ТБ · Silver · eSIM»."""
    if not label:
        return ""
    values = []
    for part in label.split(","):
        part = part.strip()
        if not part:
            continue
        values.append(part.split(":", 1)[1].strip() if ":" in part else part)
    return " · ".join(values)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("ё", "е")).strip()


def search_terms(query: str) -> list[str]:
    return [w for w in re.split(r"[\s,;]+", normalize_text(query)) if w]


@dataclass
class ProductRow:
    id: int
    parent_id: int
    type: str
    name: str
    variation_label: str
    sku: str
    permalink: str
    image_url: str
    price: int
    regular_price: int
    sale_price: int
    in_stock: bool
    category_ids: list[int]


def parse_product(raw: dict[str, Any]) -> ProductRow:
    prices = raw.get("prices") or {}
    minor = int(prices.get("currency_minor_unit", 2) or 0)
    images = raw.get("images") or []
    return ProductRow(
        id=int(raw["id"]),
        parent_id=int(raw.get("parent") or 0),
        type=str(raw.get("type") or "simple"),
        name=html.unescape(str(raw.get("name") or "")).strip(),
        variation_label=parse_variation_label(raw.get("variation")),
        sku=str(raw.get("sku") or ""),
        permalink=str(raw.get("permalink") or ""),
        image_url=str(images[0].get("src") or "") if images else "",
        price=parse_price(prices.get("price"), minor),
        regular_price=parse_price(prices.get("regular_price"), minor),
        sale_price=parse_price(prices.get("sale_price"), minor),
        in_stock=bool(raw.get("is_in_stock")),
        category_ids=[int(c["id"]) for c in raw.get("categories") or [] if "id" in c],
    )


def format_price(kopecks: int) -> str:
    """11470000 -> «114 700 ₽»; 0 -> «Цена по запросу»."""
    if not kopecks:
        return "Цена по запросу"
    rub, kop = divmod(abs(kopecks), 100)
    s = f"{rub:,}".replace(",", " ")
    if kop:
        s += f",{kop:02d}"
    return f"{'−' if kopecks < 0 else ''}{s} ₽"


def format_diff(kopecks: int) -> str:
    """Разница со знаком: −5 000 ₽ / +1 000 ₽."""
    sign = "+" if kopecks > 0 else "−"
    return sign + format_price(abs(kopecks))
