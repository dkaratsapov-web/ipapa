"""Синхронизация каталога с сайтом."""
from __future__ import annotations

import asyncio
import json
import html
import logging
import time
from dataclasses import dataclass, field
from typing import NamedTuple

import aiosqlite

from db.database import utcnow
from services.api_client import ApiError, StoreApiClient
from services.parsing import ProductRow, normalize_text, parse_product

log = logging.getLogger(__name__)

# Если пришло меньше этой доли от прошлой успешной синхронизации — не применяем.
MIN_RATIO = 0.5


class SyncError(Exception):
    pass


class State(NamedTuple):
    price: int
    in_stock: bool


class Change(NamedTuple):
    product_id: int
    old_price: int
    new_price: int
    old_in_stock: bool
    new_in_stock: bool

    @property
    def price_changed(self) -> bool:
        return is_price_change(self.old_price, self.new_price)

    @property
    def stock_changed(self) -> bool:
        return self.old_in_stock != self.new_in_stock


def is_price_change(old: int, new: int) -> bool:
    """Цена 0 — «по запросу», такие переходы изменением цены не считаем."""
    return old > 0 and new > 0 and old != new


def detect_change(product_id: int, old: State | None, new: State) -> Change | None:
    """Сравнение сохранённого и нового состояния позиции.

    Новая позиция (old is None) изменением не считается.
    """
    if old is None:
        return None
    if not is_price_change(old.price, new.price) and old.in_stock == new.in_stock:
        return None
    return Change(product_id, old.price, new.price, old.in_stock, new.in_stock)


def check_counts(
    products: int, variations: int, prev_products: int | None, prev_variations: int | None
) -> None:
    """Защита от «пустой» синхронизации."""
    if products == 0:
        raise SyncError("API вернул 0 товаров")
    if prev_products and products < prev_products * MIN_RATIO:
        raise SyncError(f"Товаров пришло {products}, в прошлый раз {prev_products} (< 50%)")
    if prev_variations and variations < prev_variations * MIN_RATIO:
        raise SyncError(f"Вариантов пришло {variations}, в прошлый раз {prev_variations} (< 50%)")


@dataclass
class SyncResult:
    ok: bool
    products_count: int = 0
    variations_count: int = 0
    categories_count: int = 0
    products_total: int = 0      # X-WP-Total
    variations_total: int = 0    # X-WP-Total
    price_changes: int = 0
    stock_changes: int = 0
    new_items: int = 0
    deactivated: int = 0
    first_sync: bool = False
    duration: float = 0.0
    error: str | None = None
    changes: list[Change] = field(default_factory=list)


class SyncService:
    def __init__(self, conn: aiosqlite.Connection, client: StoreApiClient):
        self.conn = conn
        self.client = client
        self._lock = asyncio.Lock()

    @property
    def running(self) -> bool:
        return self._lock.locked()

    async def run(self) -> SyncResult:
        async with self._lock:
            return await self._run()

    async def _run(self) -> SyncResult:
        started = time.monotonic()
        cur = await self.conn.execute(
            "INSERT INTO sync_log (started_at, status) VALUES (?, 'running')", (utcnow(),)
        )
        log_id = cur.lastrowid
        await self.conn.commit()
        try:
            result = await self._sync()
        except Exception as exc:  # noqa: BLE001 — любой сбой не должен трогать базу
            await self.conn.rollback()
            msg = str(exc) or exc.__class__.__name__
            log.error("Синхронизация не удалась: %s", msg, exc_info=not isinstance(exc, (SyncError, ApiError)))
            result = SyncResult(ok=False, error=msg)
        result.duration = time.monotonic() - started
        await self.conn.execute(
            """UPDATE sync_log SET finished_at = ?, status = ?, products_count = ?,
                   variations_count = ?, changes_count = ?, error = ? WHERE id = ?""",
            (utcnow(), "success" if result.ok else "failed", result.products_count,
             result.variations_count, result.price_changes, result.error, log_id),
        )
        await self.conn.commit()
        if result.ok:
            log.info(
                "Синхронизация: товаров %d/%d, вариантов %d/%d, изменений цен %d, наличия %d, %.1f с",
                result.products_count, result.products_total, result.variations_count,
                result.variations_total, result.price_changes, result.stock_changes, result.duration,
            )
        return result

    async def _sync(self) -> SyncResult:
        # 1. Загрузка — полностью до изменения базы
        raw_products, products_total = await self.client.fetch_products()
        raw_variations, variations_total = await self.client.fetch_variations()
        raw_categories, _ = await self.client.fetch_categories()

        products = [parse_product(p) for p in raw_products]
        variations = [parse_product(v) for v in raw_variations]
        # На случай если вариант попал и в общий список
        product_ids = {p.id for p in products}
        variations = [v for v in variations if v.id not in product_ids]

        # 2. Защита от сбоев
        async with self.conn.execute(
            """SELECT products_count, variations_count FROM sync_log
                WHERE status = 'success' ORDER BY id DESC LIMIT 1"""
        ) as cur:
            prev = await cur.fetchone()
        check_counts(len(products), len(variations),
                     prev[0] if prev else None, prev[1] if prev else None)

        # 3. Сравнение с сохранённым состоянием
        async with self.conn.execute("SELECT id, price, in_stock FROM products") as cur:
            existing = {r[0]: State(r[1], bool(r[2])) for r in await cur.fetchall()}
        first_sync = not existing

        by_id = {p.id: p for p in products}
        changes: list[Change] = []
        for item in (*products, *variations):
            if item.type == "variable":
                continue  # цена родителя — производная от вариантов
            change = detect_change(item.id, existing.get(item.id), State(item.price, item.in_stock))
            if change:
                changes.append(change)

        # 4. Запись в одной транзакции
        now = utcnow()
        all_items = [*products, *variations]
        await self.conn.executemany(
            """INSERT INTO products (id, parent_id, type, name, variation_label, sku, permalink,
                   image_url, image_thumb, gallery, price, regular_price, sale_price, in_stock,
                   is_active, category_ids, search_text, first_seen_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   parent_id = excluded.parent_id, type = excluded.type, name = excluded.name,
                   variation_label = excluded.variation_label, sku = excluded.sku,
                   permalink = excluded.permalink, image_url = excluded.image_url,
                   image_thumb = excluded.image_thumb, gallery = excluded.gallery,
                   price = excluded.price, regular_price = excluded.regular_price,
                   sale_price = excluded.sale_price, in_stock = excluded.in_stock,
                   is_active = 1, category_ids = excluded.category_ids,
                   search_text = excluded.search_text, updated_at = excluded.updated_at""",
            [self._row(item, by_id, now) for item in all_items],
        )
        seen = [item.id for item in all_items]
        await self.conn.execute("CREATE TEMP TABLE IF NOT EXISTS seen_ids (id INTEGER PRIMARY KEY)")
        await self.conn.execute("DELETE FROM seen_ids")
        await self.conn.executemany("INSERT OR IGNORE INTO seen_ids VALUES (?)", [(i,) for i in seen])
        cur = await self.conn.execute(
            """UPDATE products SET is_active = 0, updated_at = ?
                WHERE is_active = 1 AND id NOT IN (SELECT id FROM seen_ids)""",
            (now,),
        )
        deactivated = cur.rowcount

        await self.conn.executemany(
            """INSERT INTO categories (id, name, parent_id, count) VALUES (?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET name = excluded.name,
                   parent_id = excluded.parent_id, count = excluded.count""",
            [(int(c["id"]), html.unescape(str(c.get("name") or "")), int(c.get("parent") or 0),
              int(c.get("count") or 0)) for c in raw_categories],
        )

        await self.conn.executemany(
            """INSERT INTO price_history (product_id, old_price, new_price, old_in_stock,
                   new_in_stock, changed_at, notified) VALUES (?, ?, ?, ?, ?, ?, 0)""",
            [(c.product_id, c.old_price, c.new_price, int(c.old_in_stock), int(c.new_in_stock), now)
             for c in changes],
        )
        await self.conn.commit()

        return SyncResult(
            ok=True,
            products_count=len(products),
            variations_count=len(variations),
            categories_count=len(raw_categories),
            products_total=products_total,
            variations_total=variations_total,
            price_changes=sum(c.price_changed for c in changes),
            stock_changes=sum(c.stock_changed for c in changes),
            new_items=0 if first_sync else sum(1 for i in all_items if i.id not in existing),
            deactivated=deactivated,
            first_sync=first_sync,
            changes=changes,
        )

    @staticmethod
    def _row(item: ProductRow, by_id: dict[int, ProductRow], now: str) -> tuple:
        category_ids = item.category_ids
        parent_name = ""
        if item.parent_id and item.parent_id in by_id:
            parent = by_id[item.parent_id]
            parent_name = parent.name
            category_ids = category_ids or parent.category_ids
        search_text = normalize_text(" ".join(filter(None, (parent_name, item.name,
                                                            item.variation_label, item.sku))))
        cats = "|" + "|".join(map(str, category_ids)) + "|" if category_ids else ""
        return (item.id, item.parent_id, item.type, item.name, item.variation_label, item.sku,
                item.permalink, item.image_url, item.image_thumb, json.dumps(item.gallery), item.price, item.regular_price, item.sale_price,
                int(item.in_stock), cats, search_text, now, now)
