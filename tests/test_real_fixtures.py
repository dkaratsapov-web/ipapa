"""Синхронизация и выгрузка на реальных ответах сайта (tests/fixtures/real)."""
import json

import httpx

from services.api_client import StoreApiClient
from services.export import build_catalog, export_catalog
from services.parsing import parse_product
from services.sync import SyncService
from tests.conftest import FakeSite


async def test_real_data_sync_and_export(conn, tmp_path):
    site = FakeSite("real")
    api = StoreApiClient("https://shop.test/v1", min_interval=0, backoff=0, per_page=50,
                         transport=httpx.MockTransport(site.handler))
    result = await SyncService(conn, api).run()
    await api.close()
    assert result.ok, result.error
    assert result.variations_count == len(site.variations)

    # у каждого варианта есть родитель из выборки, цены — целые копейки
    parents = {p["id"] for p in site.products}
    for raw in site.variations:
        v = parse_product(raw)
        assert v.parent_id in parents
        assert v.price >= 0 and v.variation_label
        assert v.image_url and "-scaled" not in v.image_thumb

    catalog = await build_catalog(conn)
    assert len(catalog["products"]) == len(site.products)
    assert catalog["updated_at"]
    total_v = sum(len(p.get("v", [])) for p in catalog["products"])
    assert total_v == len(site.variations)
    first = catalog["products"][0]
    assert {"id", "name", "url", "img", "thumb", "cats", "price", "v"} <= first.keys()

    path = tmp_path / "catalog.json"
    await export_catalog(conn, str(path))
    assert json.loads(path.read_text(encoding="utf-8"))["products"]
