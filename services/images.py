"""Автоподбор картинок для товаров, у которых на сайте нет фото (в основном Б/У).

1. Та же модель в нашем каталоге (новый товар) — берём его фото с сайта.
2. Статья о модели в Википедии — фото из неё (свободная лицензия, API без ключей).

Результат кэшируется в таблице image_matches; промахи перепроверяются раз в неделю.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import aiosqlite
import httpx

from db.database import utcnow

log = logging.getLogger(__name__)

WIKI_API = "https://en.wikipedia.org"
USER_AGENT = "IPapaPriceBot/1.0 (https://github.com/dkaratsapov-web/ipapa)"
RETRY_MISS_AFTER = timedelta(days=7)

# Что отрезаем от названия, чтобы получить модель
_NOISE = [
    r"\b(i[3579]|m[1-5](\s*(pro|max))?)\s*/\s*\d+.*$",   # i5/8/512GB …, M1/8/256GB …
    r"\b(19|20)\d\d\b",                                  # год
    r"\b\d+\s*/\s*\d+\s*(гб|gb|тб|tb)?\b",          # 12/256 ГБ
    r"\b\d+\s*(гб|gb|тб|tb|mm|мм)\b",                 # 256 ГБ, 44mm
    r"\b(wi-?fi|cellular|lte|5g|sim|esim|nano-sim|2\s*sim|dual\s*sim)\b",
    r"\b(space\s*gr[ae]y|space\s*black|silver|gold|starlight|midnight|black|white|blue|"
    r"green|pink|purple|red|yellow|graphite|natural\s*titanium|titanium|sierra\s*blue|"
    r"deep\s*purple|cosmic\s*orange|deep\s*blue|sapce\s*gray|rose\s*gold)\b",
    r"\bбез\s+\S+.*$",                                     # «без шумоподавления»
    r"\(\d{4}\)",                                          # (2019)
]
_GENERATION = re.compile(r"\b(\d+)[-\s]*(поколени[ея]|th|nd|rd|st)\b", re.I)


def clean_model(name: str) -> str:
    """«iPhone 15 Pro Max, 256 ГБ, SIM + eSIM» -> «iPhone 15 Pro Max»."""
    s = name.split(",")[0]
    s = s.replace("″", " ").replace('"', " ").replace("&#8243;", " ")
    s = _GENERATION.sub(lambda m: f"{m[1]}", s)
    s = re.sub(r"\b(watch)\s+s(\d+)\b", r"\1 Series \2", s, flags=re.I)  # Watch S9 -> Series 9
    for pattern in _NOISE:
        s = re.sub(pattern, " ", s, flags=re.I)
    s = re.sub(r"[+/]", " ", s)
    s = re.sub(r"\(\s*\)", " ", s)
    s = re.sub(r"[а-яё]+", " ", s, flags=re.I)  # русские слова мешают поиску в en-wiki
    return re.sub(r"\s+", " ", s).strip()


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]+|\d+", text.lower())


def title_matches(model: str, title: str) -> bool:
    """Заголовок статьи должен содержать бренд/линейку и все числа модели."""
    want = _tokens(model)
    have = set(_tokens(title))
    if not want:
        return False
    numbers = [t for t in want if t.isdigit()]
    words = [t for t in want if not t.isdigit()]
    return want[0] in have and all(n in have for n in numbers) and \
        sum(w in have for w in words) >= max(1, len(words) - 1)


def resize_wiki_thumb(url: str, width: int) -> str:
    """URL миниатюры Wikimedia с нужной шириной (…/320px-File.jpg -> …/800px-File.jpg)."""
    return re.sub(r"/\d+px-", f"/{width}px-", url, count=1)


@dataclass
class Match:
    image_url: str
    thumb_url: str
    source: str


class ImageMatcher:
    def __init__(self, conn: aiosqlite.Connection, *, transport: httpx.AsyncBaseTransport | None = None,
                 min_interval: float = 1.0):
        self.conn = conn
        self.min_interval = min_interval
        self._last = 0.0
        self._client = httpx.AsyncClient(timeout=20, headers={"User-Agent": USER_AGENT},
                                         transport=transport, follow_redirects=True)

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, url: str, params: dict | None = None) -> dict | None:
        wait = self._last + self.min_interval - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        self._last = time.monotonic()
        try:
            resp = await self._client.get(url, params=params)
        except httpx.HTTPError as exc:
            log.warning("Поиск картинки: %s", exc)
            return None
        return resp.json() if resp.status_code == 200 else None

    async def from_catalog(self, product_id: int, model: str) -> Match | None:
        """Новый товар той же модели в нашем каталоге."""
        key = model.lower()
        async with self.conn.execute(
            """SELECT id, name, image_url, image_thumb FROM products
                WHERE type != 'variation' AND is_active = 1 AND image_url != '' AND id != ?""",
            (product_id,),
        ) as cur:
            rows = await cur.fetchall()
        for pid, name, img, thumb in rows:
            if clean_model(name).lower() == key:
                return Match(img, thumb or img, f"catalog:{pid}")
        return None

    async def from_wikipedia(self, model: str) -> Match | None:
        data = await self._get(f"{WIKI_API}/w/api.php", {
            "action": "query", "list": "search", "srsearch": model, "srlimit": 5, "format": "json",
        })
        for hit in (data or {}).get("query", {}).get("search", []):
            title = hit.get("title", "")
            if not title_matches(model, title):
                continue
            summary = await self._get(f"{WIKI_API}/api/rest_v1/page/summary/{quote(title.replace(' ', '_'))}")
            thumb = (summary or {}).get("thumbnail", {}).get("source")
            if thumb:
                return Match(resize_wiki_thumb(thumb, 800), resize_wiki_thumb(thumb, 300), f"wikipedia:{title}")
        return None

    async def run(self, limit: int = 40) -> int:
        """Подобрать картинки товарам без фото. Возвращает число найденных."""
        retry_before = (datetime.now(timezone.utc) - RETRY_MISS_AFTER).isoformat(timespec="microseconds")
        async with self.conn.execute(
            """SELECT p.id, p.name FROM products p
                 LEFT JOIN image_matches m ON m.product_id = p.id
                WHERE p.type != 'variation' AND p.is_active = 1 AND p.image_url = ''
                  AND (m.product_id IS NULL OR (m.image_url = '' AND m.checked_at < ?))
                ORDER BY p.id DESC LIMIT ?""",
            (retry_before, limit),
        ) as cur:
            todo = await cur.fetchall()
        found = 0
        for product_id, name in todo:
            model = clean_model(name)
            match = None
            if model:
                match = await self.from_catalog(product_id, model) or await self.from_wikipedia(model)
            await self.conn.execute(
                """INSERT INTO image_matches (product_id, query, image_url, thumb_url, source, checked_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(product_id) DO UPDATE SET query = excluded.query,
                       image_url = excluded.image_url, thumb_url = excluded.thumb_url,
                       source = excluded.source, checked_at = excluded.checked_at""",
                (product_id, model, match.image_url if match else "", match.thumb_url if match else "",
                 match.source if match else "", utcnow()),
            )
            if match:
                found += 1
                log.info("Картинка для «%s» (%s): %s", name, model, match.source)
            else:
                log.info("Картинка для «%s» (%s) не найдена", name, model)
        await self.conn.commit()
        return found
