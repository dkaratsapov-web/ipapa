"""Какие товары считаются устройствами и какие характеристики показывать в карточке бота.

Сами характеристики — в справочнике reference/specs.yaml (services/specs_ref.py).
"""
from __future__ import annotations

from typing import Iterable

import aiosqlite

from services.images import clean_model

# Что показываем в карточке бота
CARD_LABELS = ("Экран", "Процессор", "Основная камера", "Аккумулятор", "Вес")


# ---------- какие товары считаем устройствами ----------

async def accessory_category_ids(conn: aiosqlite.Connection) -> set[int]:
    """Категория «Аксессуары» и все её потомки."""
    async with conn.execute("SELECT id, name, parent_id FROM categories") as cur:
        rows = [tuple(r) for r in await cur.fetchall()]
    ids = {cid for cid, name, _ in rows if name.strip().lower().startswith("аксессуар")}
    grew = True
    while grew:
        children = {cid for cid, _, parent in rows if parent in ids and cid not in ids}
        ids |= children
        grew = bool(children)
    return ids


def device_model(name: str, category_ids: str, accessories: Iterable[int] = ()) -> str:
    """Модель устройства (clean_model, в нижнем регистре) или «», если это аксессуар."""
    cats = {int(c) for c in (category_ids or "").strip("|").split("|") if c.isdigit()}
    if cats & set(accessories):
        return ""
    model = clean_model(name)
    if len(model) < 3:
        return ""
    return model.lower()


async def load_model_images(conn: aiosqlite.Connection) -> dict[str, str]:
    """Фото моделей, подобранные раньше (кэш model_specs.image): {модель: url}."""
    async with conn.execute("SELECT model, image FROM model_specs WHERE image IS NOT NULL AND image != ''") as cur:
        return {r[0]: r[1] for r in await cur.fetchall()}


def card_specs(specs: list[list[str]], limit: int = 5) -> list[tuple[str, str]]:
    """Ключевые поля для карточки бота: сначала основные, остальные — по порядку справочника."""
    by_label = {label: value for label, value in specs}
    order = [label for label in CARD_LABELS if label in by_label]
    order += [label for label, _ in specs if label not in order and label != "Дата выхода"]
    return [(label, by_label[label]) for label in order[:limit]]
