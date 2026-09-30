"""Сколько товаров и вариантов на сайте без картинок (по всему каталогу)."""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DEFAULT_API_URL  # noqa: E402
from services.api_client import StoreApiClient  # noqa: E402


def missing(item: dict) -> bool:
    imgs = item.get("images") or []
    return not imgs or "placeholder" in str(imgs[0].get("src", "")).lower()


async def main() -> None:
    async with StoreApiClient(os.getenv("SITE_API_URL", DEFAULT_API_URL)) as api:
        products, _ = await api.fetch_products()
        variations, _ = await api.fetch_variations()
    parent_ok = {p["id"] for p in products if not missing(p)}
    no_img = [p for p in products if missing(p)]
    v_no_img = [v for v in variations if missing(v)]
    v_no_any = [v for v in v_no_img if v.get("parent") not in parent_ok]
    print(f"Товаров: {len(products)}, без картинки: {len(no_img)}")
    print(f"Вариантов: {len(variations)}, без своей картинки: {len(v_no_img)}, "
          f"без картинки и у родителя: {len(v_no_any)}")
    for p in no_img[:60]:
        print(f"  - {p['id']}: {p['name']} [{', '.join(c['name'] for c in p.get('categories', []))}]")


if __name__ == "__main__":
    asyncio.run(main())
