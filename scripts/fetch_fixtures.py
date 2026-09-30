"""Снимает ответы Store API с реального сайта и сохраняет как фикстуры тестов.

    python scripts/fetch_fixtures.py [--limit 20]

Берёт первые N товаров, их варианты и все категории. Заодно печатает
X-WP-Total / X-WP-TotalPages по каждой коллекции.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DEFAULT_API_URL  # noqa: E402
from services.api_client import StoreApiClient  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "fixtures")


def save(name: str, endpoint: str, params: dict, items: list) -> None:
    path = os.path.join(OUT, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"_note": "Реальный ответ сайта", "fetched_at": datetime.now(timezone.utc).isoformat(),
                   "endpoint": endpoint, "params": params, "items": items}, f, ensure_ascii=False, indent=1)
    print(f"  {path}: {len(items)} шт.")


async def main(limit: int, base_url: str) -> None:
    async with StoreApiClient(base_url) as api:
        for title, extra in [("products", {}), ("variations", {"type": "variation"})]:
            page = await api.get_page("/products", 1, extra)
            print(f"{title}: X-WP-Total={page.total}, X-WP-TotalPages={page.total_pages}")

        resp = await api.get("/products", {"per_page": limit, "page": 1})
        products = resp.json()
        parent_ids = [p["id"] for p in products if p.get("type") == "variable"]

        variations: list = []
        if parent_ids:
            resp = await api.get("/products", {"type": "variation", "per_page": 100,
                                               "parent": ",".join(map(str, parent_ids))})
            variations = [v for v in resp.json() if v.get("parent") in parent_ids]
        categories, total = await api.get_all("/products/categories")
        print(f"categories: X-WP-Total={total}")

    save("products", "/products", {"per_page": limit}, products)
    save("variations", "/products", {"type": "variation", "parent": parent_ids}, variations)
    save("categories", "/products/categories", {"per_page": 100}, categories)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--url", default=os.getenv("SITE_API_URL", DEFAULT_API_URL))
    args = ap.parse_args()
    asyncio.run(main(args.limit, args.url))
