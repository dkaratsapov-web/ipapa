"""Асинхронный клиент WooCommerce Store API с ограничением частоты и ретраями."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger(__name__)

USER_AGENT = "IPapaPriceBot/1.0"
PER_PAGE = 100


class ApiError(Exception):
    pass


@dataclass
class Page:
    items: list[dict[str, Any]]
    total: int
    total_pages: int


class StoreApiClient:
    def __init__(
        self,
        base_url: str,
        *,
        min_interval: float = 1.0,
        timeout: float = 30.0,
        retries: int = 3,
        backoff: float = 2.0,
        per_page: int = PER_PAGE,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.min_interval = min_interval
        self.retries = retries
        self.backoff = backoff
        self.per_page = per_page
        self._lock = asyncio.Lock()
        self._last_request = 0.0
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            transport=transport,
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "StoreApiClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def _throttle(self) -> None:
        """Не чаще одного запроса в min_interval секунд."""
        wait = self._last_request + self.min_interval - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request = time.monotonic()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            async with self._lock:
                await self._throttle()
                try:
                    resp = await self._client.get(path, params=params)
                except httpx.HTTPError as exc:
                    last_exc = exc
                    log.warning("GET %s %s: попытка %d/%d: %r", path, params, attempt, self.retries, exc)
                else:
                    if resp.status_code == 200:
                        return resp
                    last_exc = ApiError(f"HTTP {resp.status_code} для {resp.request.url}")
                    log.warning("GET %s %s: попытка %d/%d: HTTP %s",
                                path, params, attempt, self.retries, resp.status_code)
                    # 4xx (кроме 429) повторять бессмысленно
                    if 400 <= resp.status_code < 500 and resp.status_code != 429:
                        break
            if attempt < self.retries:
                await asyncio.sleep(self.backoff ** (attempt - 1))
        raise ApiError(f"Запрос {path} не удался: {last_exc}") from last_exc

    async def get_page(self, path: str, page: int, extra: dict[str, Any] | None = None) -> Page:
        params = {"per_page": self.per_page, "page": page, **(extra or {})}
        resp = await self.get(path, params)
        try:
            data = resp.json()
        except ValueError as exc:
            raise ApiError(f"Некорректный JSON от {path}") from exc
        if not isinstance(data, list):
            raise ApiError(f"Ожидался список от {path}, получено {type(data).__name__}")
        return Page(
            items=data,
            total=int(resp.headers.get("X-WP-Total", len(data))),
            total_pages=int(resp.headers.get("X-WP-TotalPages", 1)),
        )

    async def get_all(self, path: str, extra: dict[str, Any] | None = None) -> tuple[list[dict], int]:
        """Все страницы коллекции. Возвращает (элементы, X-WP-Total)."""
        first = await self.get_page(path, 1, extra)
        items = list(first.items)
        for page in range(2, first.total_pages + 1):
            items.extend((await self.get_page(path, page, extra)).items)
        # Дедупликация на случай сдвига страниц во время обхода
        unique = {int(i["id"]): i for i in items if "id" in i}
        return list(unique.values()), first.total

    async def fetch_products(self) -> tuple[list[dict], int]:
        return await self.get_all("/products")

    async def fetch_variations(self) -> tuple[list[dict], int]:
        return await self.get_all("/products", {"type": "variation"})

    async def fetch_categories(self) -> tuple[list[dict], int]:
        return await self.get_all("/products/categories")

    async def fetch_product(self, product_id: int) -> dict:
        return (await self.get(f"/products/{product_id}")).json()

    async def search(self, text: str) -> list[dict]:
        return (await self.get("/products", {"search": text, "per_page": 20})).json()
