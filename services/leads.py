"""Заявки из мини-аппа: заказ, ремонт, трейд-ин.

Своего сервера у мини-аппа нет, заявки приходят в бота:
- sendData (запуск с кнопки клавиатуры) — JSON со всеми полями;
- deep link (запуск из меню) — компактный код, остальное бот уточняет в чате.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html import escape
from typing import Any

import aiosqlite

from db.database import utcnow
from services.parsing import format_price

LEADS_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id      INTEGER NOT NULL,
    username   TEXT,
    kind       TEXT NOT NULL,        -- order / repair / tradein
    data       TEXT NOT NULL,        -- JSON
    phone      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS kv (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

# Общие с мини-аппом справочники (webapp/src/service.ts) — порядок важен для deep link
REPAIR_DEVICES = ["Телефон", "Планшет", "Ноутбук", "Часы", "Другое"]
REPAIR_PROBLEMS = ["Разбит экран", "Не заряжается, аккумулятор", "Попала вода", "Не включается", "Другое"]
KINDS = {"order": "🛒 Заказ", "repair": "🛠 Ремонт", "tradein": "♻️ Трейд-ин"}

_PHONE = re.compile(r"[^\d+]")


async def ensure_schema(conn: aiosqlite.Connection) -> None:
    await conn.executescript(LEADS_SCHEMA)
    await conn.commit()


def clean_phone(raw: str) -> str:
    digits = _PHONE.sub("", raw or "")
    return digits if 6 <= len(digits.lstrip("+")) <= 15 else ""


@dataclass
class Lead:
    kind: str
    data: dict[str, Any] = field(default_factory=dict)
    phone: str = ""


def _text(value: Any, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]


def from_web_app(payload: dict[str, Any]) -> Lead | None:
    """{"a": "lead", "kind": ..., ...} из sendData."""
    kind = payload.get("kind")
    if kind not in KINDS:
        return None
    data: dict[str, Any] = {"name": _text(payload.get("name"), 80), "comment": _text(payload.get("comment"))}
    if kind == "order":
        items = []
        for pair in payload.get("items", [])[:50]:
            try:
                pid, qty = int(pair[0]), max(1, min(99, int(pair[1])))
            except (TypeError, ValueError, IndexError):
                continue
            items.append([pid, qty])
        if not items:
            return None
        data["items"] = items
    elif kind == "repair":
        data["device"] = _text(payload.get("device"), 40)
        data["model"] = _text(payload.get("model"), 80)
        data["problem"] = _text(payload.get("problem"), 80)
    else:
        for key in ("model", "variant", "condition"):
            data[key] = _text(payload.get(key), 80)
        try:
            data["estimate"] = max(0, int(payload.get("estimate") or 0))
        except (TypeError, ValueError):
            data["estimate"] = 0
    return Lead(kind, data, clean_phone(_text(payload.get("phone"), 30)))


def from_deep_link(payload: str, tradein: dict | None = None) -> Lead | None:
    """Компактные коды из deep link.

    o5885-1_5001-2        — заказ: товар 5885 ×1, 5001 ×2
    r0_1                  — ремонт: устройство №0, проблема №1
    t~<model>~<variant>~<cond> — трейд-ин (id из прайса трейд-ина)
    """
    if re.fullmatch(r"o\d+-\d+(_\d+-\d+)*", payload):
        items = [[int(a), max(1, min(99, int(b)))] for a, b in (p.split("-") for p in payload[1:].split("_"))]
        return Lead("order", {"items": items})
    m = re.fullmatch(r"r(\d)_(\d)", payload)
    if m:
        dev, prob = int(m[1]), int(m[2])
        if dev < len(REPAIR_DEVICES) and prob < len(REPAIR_PROBLEMS):
            return Lead("repair", {"device": REPAIR_DEVICES[dev], "problem": REPAIR_PROBLEMS[prob]})
        return None
    m = re.fullmatch(r"t~([\w-]+)~([\w-]+)~(\w+)", payload)
    if m:
        est = tradein_estimate(tradein or {}, m[1], m[2], m[3])
        if est is None:
            return Lead("tradein", {"model": m[1], "variant": m[2], "condition": m[3], "estimate": 0})
        model, variant, condition, price = est
        return Lead("tradein", {"model": model, "variant": variant, "condition": condition, "estimate": price})
    return None


def tradein_estimate(data: dict, model_id: str, variant_id: str, cond_id: str) -> tuple[str, str, str, int] | None:
    """(модель, память, состояние, цена в рублях) по прайсу трейд-ина."""
    conditions = {c["id"]: c["label"] for c in data.get("conditions", [])}
    for device in data.get("devices", []):
        for model in device.get("models", []):
            if model.get("id") != model_id:
                continue
            for variant in model.get("variants", []):
                if variant.get("id") == variant_id and cond_id in variant.get("prices", {}):
                    name = model.get("name", model_id)
                    if device.get("label") and not name.lower().startswith(device["label"].lower()):
                        name = f"{device['label']} {name}"
                    return name, variant.get("label", variant_id), conditions.get(cond_id, cond_id), \
                        int(variant["prices"][cond_id])
    return None


async def save(conn: aiosqlite.Connection, tg_id: int, username: str | None, lead: Lead) -> int:
    await ensure_schema(conn)
    cur = await conn.execute(
        "INSERT INTO leads (tg_id, username, kind, data, phone, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (tg_id, username, lead.kind, json.dumps(lead.data, ensure_ascii=False), lead.phone, utcnow()),
    )
    await conn.commit()
    from services.stats import log_event
    await log_event(conn, tg_id, "lead", value=lead.kind)
    for pid, _qty in lead.data.get("items", []):
        await log_event(conn, tg_id, "order_item", pid)
    return cur.lastrowid


async def set_phone(conn: aiosqlite.Connection, tg_id: int, phone: str) -> int | None:
    """Телефон к последней заявке пользователя без телефона. Возвращает её номер."""
    await ensure_schema(conn)
    async with conn.execute(
        "SELECT id FROM leads WHERE tg_id = ? AND phone = '' ORDER BY id DESC LIMIT 1", (tg_id,)
    ) as cur:
        row = await cur.fetchone()
    if not row:
        return None
    await conn.execute("UPDATE leads SET phone = ? WHERE id = ?", (phone, row[0]))
    await conn.commit()
    return row[0]


async def recent(conn: aiosqlite.Connection, limit: int = 10) -> list[aiosqlite.Row]:
    await ensure_schema(conn)
    async with conn.execute("SELECT * FROM leads ORDER BY id DESC LIMIT ?", (limit,)) as cur:
        return list(await cur.fetchall())


async def _item_line(conn: aiosqlite.Connection, pid: int, qty: int) -> tuple[str, int]:
    async with conn.execute(
        """SELECT p.name, p.variation_label, p.price, parent.name
             FROM products p LEFT JOIN products parent ON parent.id = p.parent_id WHERE p.id = ?""",
        (pid,),
    ) as cur:
        row = await cur.fetchone()
    if not row:
        return f"• товар #{pid} × {qty}", 0
    name, label, price, parent = row
    from services.parsing import short_label
    title = f"{parent or name} {short_label(label)}".strip()
    total = price * qty
    price_txt = f" — {format_price(total)}" if price else " — цена по запросу"
    return f"• {escape(title)} × {qty}{price_txt}", total


async def describe(conn: aiosqlite.Connection, lead: Lead) -> str:
    """Текст заявки (HTML) — для менеджеров и для подтверждения клиенту."""
    d = lead.data
    lines: list[str] = []
    if lead.kind == "order":
        total = 0
        for pid, qty in d.get("items", []):
            line, subtotal = await _item_line(conn, pid, qty)
            lines.append(line)
            total += subtotal
        if total:
            lines.append(f"<b>Итого: {format_price(total)}</b>")
    elif lead.kind == "repair":
        device = " ".join(filter(None, [d.get("device"), d.get("model")]))
        lines.append(f"Устройство: {escape(device or '—')}")
        lines.append(f"Проблема: {escape(d.get('problem') or '—')}")
    else:
        lines.append(f"Модель: {escape(' '.join(filter(None, [d.get('model'), d.get('variant')])) or '—')}")
        lines.append(f"Состояние: {escape(d.get('condition') or '—')}")
        if d.get("estimate"):
            lines.append(f"Предварительная оценка: <b>до {format_price(d['estimate'] * 100)}</b>")
    if d.get("comment"):
        lines.append(f"Комментарий: {escape(d['comment'])}")
    return "\n".join(lines)
