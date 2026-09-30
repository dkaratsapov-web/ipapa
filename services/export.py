"""Выгрузка каталога в компактный JSON для мини-аппа."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import aiosqlite

log = logging.getLogger(__name__)


async def build_catalog(conn: aiosqlite.Connection) -> dict[str, Any]:
    """Каталог активных товаров с вариантами.

    Формат варианта: [id, variation_label, price, regular_price, in_stock, image_url, thumb].
    Картинки варианта пустые, если совпадают с картинкой товара.
    Цены — в копейках.
    """
    async with conn.execute(
        "SELECT id, name, parent_id, count FROM categories WHERE count > 0 ORDER BY name"
    ) as cur:
        categories = [{"id": r[0], "name": r[1], "parent": r[2], "count": r[3]}
                      for r in await cur.fetchall()]

    async with conn.execute(
        """SELECT id, parent_id, variation_label, price, regular_price, in_stock, image_url,
                  image_thumb
             FROM products WHERE type = 'variation' AND is_active = 1
            ORDER BY price = 0, price"""
    ) as cur:
        variations: dict[int, list[list[Any]]] = {}
        for vid, parent, label, price, reg, stock, img, thumb in await cur.fetchall():
            variations.setdefault(parent, []).append([vid, label, price, reg, stock, img, thumb])

    async with conn.execute(
        """SELECT id, type, name, permalink, image_url, image_thumb, category_ids, price,
                  regular_price, in_stock, sku
             FROM products WHERE type != 'variation' AND is_active = 1 ORDER BY name"""
    ) as cur:
        products = []
        for pid, ptype, name, url, img, thumb, cats, price, reg, stock, sku in await cur.fetchall():
            item: dict[str, Any] = {
                "id": pid, "name": name, "url": url, "img": img, "thumb": thumb,
                "cats": [int(c) for c in cats.strip("|").split("|") if c],
                "price": price, "reg": reg, "stock": stock,
            }
            if sku:
                item["sku"] = sku
            if ptype == "variable":
                vs = variations.get(pid, [])
                for v in vs:  # картинка варианта нужна, только если отличается
                    if v[5] == img:
                        v[5] = v[6] = ""
                item["v"] = vs
            products.append(item)

    async with conn.execute(
        "SELECT finished_at FROM sync_log WHERE status = 'success' ORDER BY id DESC LIMIT 1"
    ) as cur:
        row = await cur.fetchone()

    return {"updated_at": row[0] if row else None, "categories": categories, "products": products}


async def export_catalog(conn: aiosqlite.Connection, path: str) -> int:
    data = await build_catalog(conn)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)
    size = os.path.getsize(path)
    log.info("Каталог выгружен: %s (%d товаров, %.0f КБ)", path, len(data["products"]), size / 1024)
    return size


async def run_publish_cmd(cmd: str) -> bool:
    """Команда публикации выгрузки (например, push в ветку с данными)."""
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    out, _ = await proc.communicate()
    if proc.returncode:
        log.error("Публикация каталога не удалась (%s): %s", proc.returncode,
                  out.decode(errors="replace")[-2000:])
        return False
    log.info("Каталог опубликован")
    return True
