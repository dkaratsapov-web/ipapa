"""Выгрузка каталога в компактный JSON для мини-аппа."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import aiosqlite

from services import tradein

from services.specs import accessory_category_ids, device_model, load_specs

log = logging.getLogger(__name__)


async def build_catalog(conn: aiosqlite.Connection) -> dict[str, Any]:
    """Каталог активных товаров с вариантами.

    Формат варианта: [id, variation_label, price, regular_price, in_stock, image_url, thumb].
    Картинки варианта пустые, если совпадают с картинкой товара.
    Цены — в копейках.
    Характеристики из Википедии (если нашлись): "specs": [[подпись, значение], …], "specs_src": url.
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
        """SELECT p.id, p.type, p.name, p.permalink,
                  COALESCE(NULLIF(p.image_url, ''), m.image_url, ''),
                  COALESCE(NULLIF(p.image_thumb, ''), m.thumb_url, ''),
                  p.category_ids, p.price, p.regular_price, p.in_stock, p.sku
             FROM products p LEFT JOIN image_matches m ON m.product_id = p.id
            WHERE p.type != 'variation' AND p.is_active = 1 ORDER BY p.name"""
    ) as cur:
        rows = await cur.fetchall()

    accessories = await accessory_category_ids(conn)
    specs = await load_specs(conn)
    products = []
    for pid, ptype, name, url, img, thumb, cats, price, reg, stock, sku in rows:
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
        found = specs.get(device_model(name, cats, accessories))
        if found:
            item["specs"], item["specs_src"] = found
        products.append(item)

    async with conn.execute(
        "SELECT finished_at FROM sync_log WHERE status = 'success' ORDER BY id DESC LIMIT 1"
    ) as cur:
        row = await cur.fetchone()

    catalog: dict[str, Any] = {"updated_at": row[0] if row else None, "categories": categories, "products": products}
    tradein_data = await tradein.load(conn)
    if tradein_data:
        catalog["tradein"] = tradein_data  # прайс калькулятора трейд-ина с сайта
    return catalog


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
