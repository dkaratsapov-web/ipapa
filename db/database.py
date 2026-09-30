"""Подключение к SQLite и схема БД."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    parent_id INTEGER NOT NULL DEFAULT 0,
    count     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY,
    parent_id       INTEGER NOT NULL DEFAULT 0,
    type            TEXT NOT NULL,
    name            TEXT NOT NULL,
    variation_label TEXT NOT NULL DEFAULT '',
    sku             TEXT NOT NULL DEFAULT '',
    permalink       TEXT NOT NULL DEFAULT '',
    image_url       TEXT NOT NULL DEFAULT '',
    image_thumb     TEXT NOT NULL DEFAULT '',
    price           INTEGER NOT NULL DEFAULT 0,  -- копейки
    regular_price   INTEGER NOT NULL DEFAULT 0,
    sale_price      INTEGER NOT NULL DEFAULT 0,
    in_stock        INTEGER NOT NULL DEFAULT 0,
    is_active       INTEGER NOT NULL DEFAULT 1,
    category_ids    TEXT NOT NULL DEFAULT '',    -- формат "|12|34|"
    search_text     TEXT NOT NULL DEFAULT '',    -- нормализованный текст для поиска
    first_seen_at   TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_products_parent ON products(parent_id);

CREATE TABLE IF NOT EXISTS price_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id   INTEGER NOT NULL,
    old_price    INTEGER NOT NULL,
    new_price    INTEGER NOT NULL,
    old_in_stock INTEGER NOT NULL,
    new_in_stock INTEGER NOT NULL,
    changed_at   TEXT NOT NULL,
    notified     INTEGER NOT NULL DEFAULT 0   -- очередь уведомлений подписчикам
);
CREATE INDEX IF NOT EXISTS ix_history_changed ON price_history(changed_at);
CREATE INDEX IF NOT EXISTS ix_history_notified ON price_history(notified);

CREATE TABLE IF NOT EXISTS users (
    tg_id      INTEGER PRIMARY KEY,
    username   TEXT,
    first_seen TEXT NOT NULL,
    is_admin   INTEGER NOT NULL DEFAULT 0,
    is_active  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id      INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (tg_id, product_id)
);
CREATE INDEX IF NOT EXISTS ix_subs_product ON subscriptions(product_id);

CREATE TABLE IF NOT EXISTS image_matches (
    product_id INTEGER PRIMARY KEY,
    query      TEXT NOT NULL,
    image_url  TEXT NOT NULL DEFAULT '',   -- пусто — не нашли
    thumb_url  TEXT NOT NULL DEFAULT '',
    source     TEXT NOT NULL DEFAULT '',   -- catalog:<id> / wikipedia:<статья>
    checked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_specs (
    model      TEXT PRIMARY KEY,               -- clean_model(name).lower()
    title      TEXT NOT NULL DEFAULT '',       -- статья Википедии
    url        TEXT NOT NULL DEFAULT '',
    specs      TEXT NOT NULL DEFAULT '[]',     -- JSON [[подпись, значение], …]; [] — не нашли
    checked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    status           TEXT NOT NULL,             -- running / success / failed
    products_count   INTEGER NOT NULL DEFAULT 0,
    variations_count INTEGER NOT NULL DEFAULT 0,
    changes_count    INTEGER NOT NULL DEFAULT 0,
    error            TEXT
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


# Колонки, добавленные после первой версии схемы: (таблица, колонка, определение)
MIGRATIONS = [
    ("products", "image_thumb", "TEXT NOT NULL DEFAULT ''"),
]


async def migrate(conn: aiosqlite.Connection) -> None:
    for table, column, definition in MIGRATIONS:
        async with conn.execute(f"PRAGMA table_info({table})") as cur:
            columns = {row[1] for row in await cur.fetchall()}
        if column not in columns:
            await conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


async def connect(path: str) -> aiosqlite.Connection:
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.executescript(SCHEMA)
    await migrate(conn)
    await conn.commit()
    return conn
