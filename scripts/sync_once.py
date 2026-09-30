"""Разовая синхронизация без бота: печатает итог и 5 примеров цен.

    python scripts/sync_once.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

from config import DEFAULT_API_URL  # noqa: E402
from db.database import connect  # noqa: E402
from services.api_client import StoreApiClient  # noqa: E402
from services.parsing import format_price, short_label  # noqa: E402
from services.sync import SyncService  # noqa: E402


async def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    conn = await connect(os.getenv("DB_PATH", "data/ipapa.db"))
    async with StoreApiClient(os.getenv("SITE_API_URL", DEFAULT_API_URL)) as api:
        result = await SyncService(conn, api).run()
    if not result.ok:
        await conn.close()
        print("ОШИБКА:", result.error)
        sys.exit(1)
    print(f"Товаров: {result.products_count} (X-WP-Total {result.products_total})")
    print(f"Вариантов: {result.variations_count} (X-WP-Total {result.variations_total})")
    print(f"Категорий: {result.categories_count}, изменений цен: {result.price_changes}, "
          f"время {result.duration:.1f} с\n")
    async with conn.execute(
        """SELECT v.variation_label, v.price, v.in_stock, p.name FROM products v
             JOIN products p ON p.id = v.parent_id
            WHERE v.type = 'variation' AND v.is_active = 1 AND v.price > 0
            ORDER BY RANDOM() LIMIT 5"""
    ) as cur:
        for label, price, stock, name in await cur.fetchall():
            print(f"{'✅' if stock else '❌'} {name} {short_label(label)} — {format_price(price)}")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
