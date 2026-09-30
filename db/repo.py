"""Запросы к БД."""
from __future__ import annotations

from typing import Any, Iterable

import aiosqlite

from db.database import utcnow

# Карточка «родительского» товара с минимальной ценой по активным вариантам.
_PRODUCT_SUMMARY = """
SELECT p.*,
       COALESCE(
           (SELECT MIN(v.price) FROM products v
             WHERE v.parent_id = p.id AND v.is_active = 1 AND v.price > 0),
           NULLIF(p.price, 0), 0) AS min_price,
       COALESCE(
           (SELECT MAX(v.in_stock) FROM products v
             WHERE v.parent_id = p.id AND v.is_active = 1),
           p.in_stock) AS any_stock
  FROM products p
"""

# Условие «значимого» изменения цены: цена по запросу (0) не учитывается.
PRICE_CHANGED_SQL = "h.old_price > 0 AND h.new_price > 0 AND h.old_price != h.new_price"


class Repo:
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def _all(self, sql: str, params: Iterable[Any] = ()) -> list[aiosqlite.Row]:
        async with self.conn.execute(sql, tuple(params)) as cur:
            return list(await cur.fetchall())

    async def _one(self, sql: str, params: Iterable[Any] = ()) -> aiosqlite.Row | None:
        async with self.conn.execute(sql, tuple(params)) as cur:
            return await cur.fetchone()

    async def _scalar(self, sql: str, params: Iterable[Any] = ()) -> Any:
        row = await self._one(sql, params)
        return row[0] if row else None

    # ---------- пользователи ----------

    async def upsert_user(self, tg_id: int, username: str | None, is_admin: bool) -> None:
        await self.conn.execute(
            """INSERT INTO users (tg_id, username, first_seen, is_admin, is_active)
               VALUES (?, ?, ?, ?, 1)
               ON CONFLICT(tg_id) DO UPDATE SET
                   username = excluded.username,
                   is_admin = excluded.is_admin,
                   is_active = 1""",
            (tg_id, username, utcnow(), int(is_admin)),
        )
        await self.conn.commit()

    async def mark_user_inactive(self, tg_id: int) -> None:
        await self.conn.execute("UPDATE users SET is_active = 0 WHERE tg_id = ?", (tg_id,))
        await self.conn.commit()

    async def count_users(self) -> tuple[int, int]:
        row = await self._one("SELECT COUNT(*), COALESCE(SUM(is_active), 0) FROM users")
        return row[0], row[1]

    # ---------- каталог ----------

    async def top_categories(self) -> list[aiosqlite.Row]:
        return await self._all(
            "SELECT * FROM categories WHERE parent_id = 0 AND count > 0 ORDER BY name"
        )

    async def child_categories(self, parent_id: int) -> list[aiosqlite.Row]:
        return await self._all(
            "SELECT * FROM categories WHERE parent_id = ? AND count > 0 ORDER BY name",
            (parent_id,),
        )

    async def get_category(self, cat_id: int) -> aiosqlite.Row | None:
        return await self._one("SELECT * FROM categories WHERE id = ?", (cat_id,))

    async def category_products(
        self, cat_id: int, offset: int, limit: int
    ) -> tuple[list[aiosqlite.Row], int]:
        where = "WHERE p.type != 'variation' AND p.is_active = 1 AND p.category_ids LIKE ?"
        like = f"%|{cat_id}|%"
        total = await self._scalar(f"SELECT COUNT(*) FROM products p {where}", (like,))
        rows = await self._all(
            f"{_PRODUCT_SUMMARY} {where} ORDER BY any_stock DESC, p.name LIMIT ? OFFSET ?",
            (like, limit, offset),
        )
        return rows, total or 0

    async def get_product(self, product_id: int) -> aiosqlite.Row | None:
        """Товар; пустая картинка заменяется подобранной автоматически (image_matches)."""
        return await self._one(
            # подобранная картинка идёт первой: sqlite3.Row отдаёт первую колонку с таким именем
            """SELECT COALESCE(NULLIF(p.image_url, ''), m.image_url, '') AS image_url, p.*
                 FROM products p LEFT JOIN image_matches m ON m.product_id = p.id
                WHERE p.id = ?""",
            (product_id,),
        )

    async def get_product_summary(self, product_id: int) -> aiosqlite.Row | None:
        return await self._one(f"{_PRODUCT_SUMMARY} WHERE p.id = ?", (product_id,))

    async def get_variations(self, parent_id: int) -> list[aiosqlite.Row]:
        """Активные варианты, отсортированные по цене («по запросу» — в конце)."""
        return await self._all(
            """SELECT * FROM products
                WHERE parent_id = ? AND is_active = 1
                ORDER BY price = 0, price, variation_label""",
            (parent_id,),
        )

    async def search(self, terms: list[str], limit: int = 10) -> list[aiosqlite.Row]:
        """Поиск по всем словам в названии товара и описании варианта."""
        if not terms:
            return []
        cond = " AND ".join("search_text LIKE ?" for _ in terms)
        params = [f"%{t}%" for t in terms]
        rows = await self._all(
            f"""SELECT DISTINCT CASE WHEN type = 'variation' THEN parent_id ELSE id END AS pid
                  FROM products WHERE is_active = 1 AND {cond}""",
            params,
        )
        ids = [r["pid"] for r in rows]
        if not ids:
            return []
        marks = ",".join("?" * len(ids))
        return await self._all(
            f"""{_PRODUCT_SUMMARY}
                WHERE p.id IN ({marks}) AND p.is_active = 1
                ORDER BY any_stock DESC, LENGTH(p.name), p.name LIMIT ?""",
            [*ids, limit],
        )

    async def last_update_time(self) -> str | None:
        return await self._scalar(
            "SELECT finished_at FROM sync_log WHERE status = 'success' ORDER BY id DESC LIMIT 1"
        )

    # ---------- подписки ----------

    async def add_subscription(self, tg_id: int, product_id: int) -> bool:
        cur = await self.conn.execute(
            "INSERT OR IGNORE INTO subscriptions (tg_id, product_id, created_at) VALUES (?, ?, ?)",
            (tg_id, product_id, utcnow()),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def remove_subscription(self, tg_id: int, sub_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM subscriptions WHERE id = ? AND tg_id = ?", (sub_id, tg_id)
        )
        await self.conn.commit()

    async def remove_subscription_by_product(self, tg_id: int, product_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM subscriptions WHERE tg_id = ? AND product_id = ?", (tg_id, product_id)
        )
        await self.conn.commit()

    async def user_subscriptions(self, tg_id: int) -> list[aiosqlite.Row]:
        return await self._all(
            """SELECT s.id AS sub_id, s.product_id, p.name, p.type, p.variation_label,
                      p.price, p.parent_id, parent.name AS parent_name
                 FROM subscriptions s
                 LEFT JOIN products p ON p.id = s.product_id
                 LEFT JOIN products parent ON parent.id = p.parent_id
                WHERE s.tg_id = ? ORDER BY s.id""",
            (tg_id,),
        )

    async def subscribed_ids(self, tg_id: int) -> set[int]:
        rows = await self._all("SELECT product_id FROM subscriptions WHERE tg_id = ?", (tg_id,))
        return {r[0] for r in rows}

    async def count_subscriptions(self) -> int:
        return await self._scalar("SELECT COUNT(*) FROM subscriptions") or 0

    # ---------- уведомления ----------

    async def pending_events(self) -> list[aiosqlite.Row]:
        return await self._all(
            """SELECT h.*, p.name, p.variation_label, p.permalink, p.parent_id,
                      parent.name AS parent_name, parent.permalink AS parent_permalink
                 FROM price_history h
                 JOIN products p ON p.id = h.product_id
                 LEFT JOIN products parent ON parent.id = p.parent_id
                WHERE h.notified = 0 ORDER BY h.id"""
        )

    async def subscribers_for(self, product_id: int, parent_id: int) -> list[int]:
        rows = await self._all(
            """SELECT DISTINCT s.tg_id FROM subscriptions s
                 JOIN users u ON u.tg_id = s.tg_id AND u.is_active = 1
                WHERE s.product_id IN (?, ?)""",
            (product_id, parent_id or product_id),
        )
        return [r[0] for r in rows]

    async def mark_notified(self, event_ids: list[int]) -> None:
        if not event_ids:
            return
        marks = ",".join("?" * len(event_ids))
        await self.conn.execute(
            f"UPDATE price_history SET notified = 1 WHERE id IN ({marks})", event_ids
        )
        await self.conn.commit()

    # ---------- отчёты ----------

    _HISTORY_SELECT = """
        SELECT h.*, p.name, p.variation_label, p.permalink, p.parent_id,
               parent.name AS parent_name, parent.permalink AS parent_permalink
          FROM price_history h
          JOIN products p ON p.id = h.product_id
          LEFT JOIN products parent ON parent.id = p.parent_id
    """

    async def price_changes_since(self, since_iso: str) -> list[aiosqlite.Row]:
        return await self._all(
            f"""{self._HISTORY_SELECT}
                WHERE h.changed_at >= ? AND {PRICE_CHANGED_SQL}
                ORDER BY h.changed_at DESC, h.id DESC""",
            (since_iso,),
        )

    async def out_of_stock_since(self, since_iso: str) -> list[aiosqlite.Row]:
        return await self._all(
            f"""{self._HISTORY_SELECT}
                WHERE h.changed_at >= ? AND h.old_in_stock = 1 AND h.new_in_stock = 0
                ORDER BY h.changed_at DESC""",
            (since_iso,),
        )

    async def new_products_since(self, since_iso: str) -> list[aiosqlite.Row]:
        """Новые карточки товаров (без первой синхронизации, когда «новое» всё)."""
        first_sync = await self._scalar(
            "SELECT MIN(finished_at) FROM sync_log WHERE status = 'success'"
        )
        if not first_sync:
            return []
        return await self._all(
            f"""{_PRODUCT_SUMMARY}
                WHERE p.type != 'variation' AND p.is_active = 1
                  AND p.first_seen_at >= ? AND p.first_seen_at > ?
                ORDER BY p.name""",
            (since_iso, first_sync),
        )

    async def last_sync(self, status: str | None = None) -> aiosqlite.Row | None:
        if status:
            return await self._one(
                "SELECT * FROM sync_log WHERE status = ? ORDER BY id DESC LIMIT 1", (status,)
            )
        return await self._one("SELECT * FROM sync_log ORDER BY id DESC LIMIT 1")

    async def product_counts(self) -> tuple[int, int]:
        row = await self._one(
            """SELECT COALESCE(SUM(type != 'variation'), 0), COALESCE(SUM(type = 'variation'), 0)
                 FROM products WHERE is_active = 1"""
        )
        return row[0], row[1]
