"""Внутренняя статистика: события пользователей и отчёт для администраторов.

События пишет бот (старт, просмотры карточек и поиски в боте, подписки, заявки) и
мини-апп — пачкой вместе с ближайшей отправкой данных в бота (sendData).
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from typing import Any, Iterable

import aiosqlite

from db.database import utcnow

log = logging.getLogger(__name__)

STATS_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT NOT NULL,
    tg_id      INTEGER,
    kind       TEXT NOT NULL,     -- start, bot_view, bot_search, sub_add, sub_del, lead, order_item,
                                  -- app_open, app_view, app_fav, app_cart, app_search, app_compare
    product_id INTEGER,
    value      TEXT
);
CREATE INDEX IF NOT EXISTS ix_events_kind_ts ON events(kind, ts);
"""

_ready: set[int] = set()


async def ensure_schema(conn: aiosqlite.Connection) -> None:
    if id(conn) in _ready:
        return
    await conn.executescript(STATS_SCHEMA)
    await conn.commit()
    _ready.add(id(conn))


async def log_event(conn: aiosqlite.Connection, tg_id: int | None, kind: str,
                    product_id: int | None = None, value: str | None = None) -> None:
    """Записать событие; сбой статистики не должен мешать боту."""
    try:
        await ensure_schema(conn)
        await conn.execute(
            "INSERT INTO events (ts, tg_id, kind, product_id, value) VALUES (?, ?, ?, ?, ?)",
            (utcnow(), tg_id, kind, product_id, (value or "")[:120] or None),
        )
        await conn.commit()
    except Exception:  # noqa: BLE001
        log.exception("Не удалось записать событие статистики %s", kind)


async def log_app_batch(conn: aiosqlite.Connection, tg_id: int, batch: Any) -> int:
    """События мини-аппа из sendData: {"v": {id: n}, "f": [id], "c": [id], "q": [str], "k": [id]}."""
    if not isinstance(batch, dict):
        return 0
    rows: list[tuple] = []
    now = utcnow()

    def ids(key: str) -> Iterable[int]:
        for x in (batch.get(key) or [])[:100]:
            try:
                yield int(x)
            except (TypeError, ValueError):
                continue

    views = batch.get("v") or {}
    if isinstance(views, dict):
        for pid, n in list(views.items())[:200]:
            try:
                rows += [(now, tg_id, "app_view", int(pid), None)] * max(1, min(int(n), 20))
            except (TypeError, ValueError):
                continue
    rows += [(now, tg_id, "app_fav", pid, None) for pid in ids("f")]
    rows += [(now, tg_id, "app_cart", pid, None) for pid in ids("c")]
    rows += [(now, tg_id, "app_compare", pid, None) for pid in ids("k")]
    rows += [(now, tg_id, "app_search", None, str(q)[:120]) for q in (batch.get("q") or [])[:50] if str(q).strip()]
    rows.append((now, tg_id, "app_open", None, None))
    await ensure_schema(conn)
    await conn.executemany("INSERT INTO events (ts, tg_id, kind, product_id, value) VALUES (?, ?, ?, ?, ?)", rows)
    await conn.commit()
    return len(rows)


# ---------- отчёт ----------

def _since(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="microseconds")


async def _scalar(conn: aiosqlite.Connection, sql: str, params: Iterable[Any] = ()) -> int:
    async with conn.execute(sql, tuple(params)) as cur:
        row = await cur.fetchone()
    return int(row[0] or 0) if row else 0


async def _top_products(conn: aiosqlite.Connection, kinds: tuple[str, ...], since: str,
                        limit: int = 10) -> list[tuple[str, int]]:
    marks = ",".join("?" * len(kinds))
    async with conn.execute(
        f"""SELECT COALESCE(parent.name, p.name, 'товар #' || e.product_id) AS title, COUNT(*) AS n
              FROM events e
              LEFT JOIN products p ON p.id = e.product_id
              LEFT JOIN products parent ON parent.id = p.parent_id
             WHERE e.kind IN ({marks}) AND e.ts >= ? AND e.product_id IS NOT NULL
             GROUP BY title ORDER BY n DESC LIMIT ?""",
        (*kinds, since, limit),
    ) as cur:
        return [(r[0], r[1]) for r in await cur.fetchall()]


async def _top_queries(conn: aiosqlite.Connection, since: str, limit: int = 10) -> list[tuple[str, int]]:
    async with conn.execute(
        "SELECT value FROM events WHERE kind IN ('bot_search', 'app_search') AND ts >= ? AND value IS NOT NULL",
        (since,),
    ) as cur:
        queries = Counter(" ".join(r[0].lower().split()) for r in await cur.fetchall())
    return queries.most_common(limit)


def _top_lines(title: str, rows: list[tuple[str, int]]) -> list[str]:
    if not rows:
        return []
    return ["", f"<b>{title}</b>", *(f"{i}. {escape(name)} — {n}" for i, (name, n) in enumerate(rows, 1))]


async def full_report(conn: aiosqlite.Connection, days: int = 7) -> list[str]:
    """Отчёт для /stats: пользователи, заявки, подписки, популярное за `days` дней."""
    await ensure_schema(conn)
    from services.leads import ensure_schema as ensure_leads
    await ensure_leads(conn)
    d1, d7, d30, period = _since(1), _since(7), _since(30), _since(days)

    users = await _scalar(conn, "SELECT COUNT(*) FROM users")
    active = await _scalar(conn, "SELECT COUNT(*) FROM users WHERE is_active = 1")
    new = [await _scalar(conn, "SELECT COUNT(*) FROM users WHERE first_seen >= ?", (s,)) for s in (d1, d7, d30)]
    app_users = await _scalar(conn, "SELECT COUNT(DISTINCT tg_id) FROM events WHERE kind LIKE 'app_%' AND ts >= ?", (period,))
    bot_users = await _scalar(
        conn, "SELECT COUNT(DISTINCT tg_id) FROM events WHERE kind IN ('start','bot_view','bot_search') AND ts >= ?", (period,))

    async with conn.execute(
        """SELECT kind, SUM(created_at >= ?), SUM(created_at >= ?), SUM(created_at >= ?), COUNT(*),
                  SUM(phone != '') FROM leads GROUP BY kind""",
        (d1, d7, d30),
    ) as cur:
        leads = {r[0]: r[1:] for r in await cur.fetchall()}
    subs = await _scalar(conn, "SELECT COUNT(*) FROM subscriptions")
    subs_users = await _scalar(conn, "SELECT COUNT(DISTINCT tg_id) FROM subscriptions")

    names = {"order": "🛒 Заказы", "repair": "🛠 Ремонт", "tradein": "♻️ Трейд-ин"}
    lines = [
        f"📊 <b>Статистика</b> · популярное за {days} дн.",
        "",
        "<b>👥 Пользователи</b>",
        f"Всего: {users}, активных: {active} (заблокировали бота: {users - active})",
        f"Новых: сегодня {new[0]} · за 7 дн. {new[1]} · за 30 дн. {new[2]}",
        f"Пользовались за {days} дн.: ботом {bot_users}, приложением {app_users}*",
        "",
        "<b>📨 Заявки</b> (сутки · 7 дн. · 30 дн. · всего)",
    ]
    if leads:
        for kind, label in names.items():
            if kind in leads:
                a, b, c, total, with_phone = leads[kind]
                lines.append(f"{label}: {a or 0} · {b or 0} · {c or 0} · {total} (с телефоном: {with_phone or 0})")
    else:
        lines.append("Пока нет")
    lines += ["", "<b>🔔 Подписки на цену</b>", f"Всего: {subs} у {subs_users} пользователей"]

    async with conn.execute(
        """SELECT COALESCE(parent.name, p.name, 'товар #' || s.product_id) AS title, COUNT(*) AS n
             FROM subscriptions s LEFT JOIN products p ON p.id = s.product_id
             LEFT JOIN products parent ON parent.id = p.parent_id
            GROUP BY title ORDER BY n DESC LIMIT 5"""
    ) as cur:
        lines += _top_lines("Чаще всего следят", [(r[0], r[1]) for r in await cur.fetchall()])[1:]

    lines += _top_lines("👀 Популярные карточки", await _top_products(conn, ("bot_view", "app_view"), period))
    lines += _top_lines("❤️ Добавляют в избранное", await _top_products(conn, ("app_fav",), period))
    lines += _top_lines("🛒 Добавляют в корзину", await _top_products(conn, ("app_cart",), period))
    lines += _top_lines("📦 Заказывают", await _top_products(conn, ("order_item",), period))
    lines += _top_lines("⚖️ Сравнивают", await _top_products(conn, ("app_compare",), period))
    lines += _top_lines("🔎 Частые запросы", await _top_queries(conn, period))
    lines += ["", "<i>* События мини-аппа приходят вместе с заявками и сохранением подписок — "
                  "это часть картины. Полная — в Яндекс Метрике, если подключена.</i>"]

    from bot.formatting import split_messages
    return split_messages(lines)


async def digest_lines(conn: aiosqlite.Connection) -> list[str]:
    """Короткий блок для ежедневной сводки."""
    await ensure_schema(conn)
    from services.leads import ensure_schema as ensure_leads
    await ensure_leads(conn)
    d1 = _since(1)
    new_users = await _scalar(conn, "SELECT COUNT(*) FROM users WHERE first_seen >= ?", (d1,))
    leads = await _scalar(conn, "SELECT COUNT(*) FROM leads WHERE created_at >= ?", (d1,))
    top = await _top_products(conn, ("bot_view", "app_view"), d1, 3)
    out = ["", "<b>Пользователи и заявки за сутки</b>", f"Новых пользователей: {new_users}, заявок: {leads}"]
    if top:
        out.append("Смотрели чаще всего: " + ", ".join(escape(n) for n, _ in top))
    return out
