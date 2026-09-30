from __future__ import annotations

import copy
import json
import os
import sys
from typing import Any

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import connect  # noqa: E402
from db.repo import Repo  # noqa: E402
from services.api_client import StoreApiClient  # noqa: E402
from services.sync import SyncService  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name: str) -> list[dict[str, Any]]:
    with open(os.path.join(FIXTURES, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)["items"]


class FakeSite:
    """Имитация Store API: пагинация, заголовки X-WP-*, сбои по запросу."""

    def __init__(self) -> None:
        self.products = load_fixture("products")
        self.variations = load_fixture("variations")
        self.categories = load_fixture("categories")
        self.fail_status: int | None = None
        self.fail_on: str | None = None  # "variation" — падать только на вариантах
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        params = request.url.params
        path = request.url.path
        if path.endswith("/products/categories"):
            items = self.categories
        elif path.endswith("/products"):
            items = self.variations if params.get("type") == "variation" else self.products
        else:
            return httpx.Response(404, json={"code": "rest_no_route"})
        if self.fail_status and (self.fail_on is None or self.fail_on == params.get("type")):
            return httpx.Response(self.fail_status, text="error")
        per_page = int(params.get("per_page", 10))
        page = int(params.get("page", 1))
        chunk = items[(page - 1) * per_page: page * per_page]
        pages = max(1, -(-len(items) // per_page))
        return httpx.Response(200, json=copy.deepcopy(chunk),
                              headers={"X-WP-Total": str(len(items)), "X-WP-TotalPages": str(pages)})


@pytest.fixture
def site() -> FakeSite:
    return FakeSite()


@pytest.fixture
async def client(site: FakeSite):
    api = StoreApiClient("https://shop.test/wp-json/wc/store/v1", min_interval=0, backoff=0,
                         per_page=3, transport=httpx.MockTransport(site.handler))
    yield api
    await api.close()


@pytest.fixture
async def conn():
    c = await connect(":memory:")
    yield c
    await c.close()


@pytest.fixture
def repo(conn) -> Repo:
    return Repo(conn)


@pytest.fixture
def sync(conn, client) -> SyncService:
    return SyncService(conn, client)
