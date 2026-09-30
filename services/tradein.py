"""Прайс трейд-ина с сайта (страница /trade-in/, объект window.ipapaTradeInCalculator).

Забираем при каждой синхронизации (1 запрос), храним в kv и выгружаем в каталог —
калькулятор в мини-аппе считает по тем же ценам, что и сайт.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import aiosqlite

from db.database import utcnow
from services.api_client import StoreApiClient
from services.leads import ensure_schema

log = logging.getLogger(__name__)
KV_KEY = "tradein"
_DATA = re.compile(r"ipapaTradeInCalculator\s*=\s*(\{.*?\})\s*;\s*(?:\n|</script>|//)", re.S)


def parse_tradein_page(page: str) -> dict[str, Any] | None:
    """Прайс со страницы; None — если структура не распознана."""
    m = _DATA.search(page)
    if not m:
        return None
    try:
        raw = json.loads(m[1])
    except ValueError:
        return None
    conditions = [{"id": str(c["id"]), "label": str(c["label"])}
                  for c in raw.get("conditions", []) if c.get("id") and c.get("label")]
    cond_ids = {c["id"] for c in conditions}
    devices = []
    for dev in raw.get("devices", []):
        models = []
        for model in dev.get("models", []):
            variants = []
            for v in model.get("variants", []):
                prices = {k: int(p) for k, p in (v.get("prices") or {}).items()
                          if k in cond_ids and str(p).lstrip("-").isdigit() and int(p) > 0}
                if prices:
                    variants.append({"id": str(v.get("id")), "label": str(v.get("label") or v.get("id")),
                                     "prices": prices})
            if model.get("id") and variants:
                models.append({"id": str(model["id"]), "name": str(model.get("name") or model["id"]).strip(),
                               "variants": variants})
        if dev.get("slug") and models:
            devices.append({"slug": str(dev["slug"]), "label": str(dev.get("label") or dev["slug"]),
                            "models": models})
    if not conditions or not devices:
        return None
    return {"conditions": conditions, "devices": devices}


async def refresh(conn: aiosqlite.Connection, client: StoreApiClient, site_url: str) -> bool:
    """Обновить прайс. При сбое остаётся прошлый."""
    try:
        resp = await client.get(f"{site_url.rstrip('/')}/trade-in/")
        data = parse_tradein_page(resp.text)
    except Exception as exc:  # noqa: BLE001 — прайс трейд-ина не должен ломать синхронизацию
        log.warning("Прайс трейд-ина не загружен: %s", exc)
        return False
    if not data:
        log.warning("Прайс трейд-ина: структура страницы не распознана")
        return False
    await ensure_schema(conn)
    await conn.execute(
        """INSERT INTO kv (key, value, updated_at) VALUES (?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
        (KV_KEY, json.dumps(data, ensure_ascii=False), utcnow()),
    )
    await conn.commit()
    models = sum(len(d["models"]) for d in data["devices"])
    log.info("Прайс трейд-ина: %d моделей", models)
    return True


async def load(conn: aiosqlite.Connection) -> dict[str, Any] | None:
    await ensure_schema(conn)
    async with conn.execute("SELECT value FROM kv WHERE key = ?", (KV_KEY,)) as cur:
        row = await cur.fetchone()
    return json.loads(row[0]) if row else None
