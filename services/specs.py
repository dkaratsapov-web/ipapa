"""Технические характеристики устройств из Википедии (на сайте магазина их нет).

Ищем статью о модели в английской Википедии, берём шаблон {{Infobox …}} из вводной
секции и переводим ключевые поля на русский. Работаем по модели, а не по товару:
десяток Б/У «iPhone 15 Pro, 256 ГБ» — один запрос.

Результат кэшируется в таблице model_specs (ключ — clean_model(name).lower());
промахи перепроверяются раз в неделю.
"""
from __future__ import annotations

import asyncio
import html
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import quote

import aiosqlite
import httpx

from db.database import utcnow
from services.images import RETRY_MISS_AFTER, USER_AGENT, WIKI_API, _tokens, clean_model, title_matches

log = logging.getLogger(__name__)

MAX_SPECS = 12
MAX_VALUE = 180

# Русская подпись -> ключи инфобокса (берётся первый заполненный)
SPEC_FIELDS: list[tuple[str, tuple[str, ...]]] = [
    ("Экран", ("display", "screen")),
    ("Процессор", ("soc", "cpu", "processor", "chip")),
    ("Оперативная память", ("memory", "ram")),
    ("Основная камера", ("rear_camera", "camera")),
    ("Фронтальная камера", ("front_camera",)),
    ("Аккумулятор", ("battery", "power")),
    ("Зарядка", ("charging",)),
    ("Влагозащита", ("water_resistance", "water")),
    ("ОС", ("os", "operatingsystem", "operating_system")),
    ("Размеры", ("dimensions", "size")),
    ("Вес", ("weight", "mass")),
    ("Дата выхода", ("releasedate", "release_date", "first_release", "released", "introduced")),
]

# Что показываем в карточке бота
CARD_LABELS = ("Экран", "Процессор", "Основная камера", "Аккумулятор", "Вес")

_LIST_TEMPLATES = {"ubl", "unbulleted list", "ublist", "plainlist", "plain list", "flatlist",
                   "flat list", "hlist", "bulleted list", "blist"}
_INLINE_TEMPLATES = {"nowrap", "nobr", "small", "big", "abbr", "nowrap begin", "lang", "resize"}
_DATE_TEMPLATES = {"start date", "start date and age", "release date", "release date and age",
                   "date", "end date"}
_RANGE_WORDS = {"-", "–", "to", "and", "or", "x", "×", "by"}  # {{convert|1|to|2|in}}


# ---------- разбор викитекста ----------

def _strip_refs(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<ref\b[^>]*/\s*>", "", text, flags=re.I)                 # <ref name="x" />
    text = re.sub(r"<ref\b[^>]*>.*?</ref\s*>", "", text, flags=re.I | re.S)  # <ref>…</ref>
    return text


def find_infobox(wikitext: str) -> str | None:
    """Содержимое первого {{Infobox …}} (без внешних скобок) с учётом вложенных шаблонов."""
    m = re.search(r"\{\{\s*infobox\b", wikitext, re.I)
    if not m:
        return None
    depth, i, start = 0, m.start(), m.start()
    while i < len(wikitext):
        if wikitext.startswith("{{", i):
            depth += 1
            i += 2
        elif wikitext.startswith("}}", i):
            depth -= 1
            i += 2
            if depth == 0:
                return wikitext[start + 2:i - 2]
        else:
            i += 1
    return None  # скобки не закрыты


def _split_top(text: str, sep: str) -> list[str]:
    """Режет по sep только на верхнем уровне (вне {{…}} и [[…]])."""
    parts, depth_t, depth_l, last, i = [], 0, 0, 0, 0
    while i < len(text):
        two = text[i:i + 2]
        if two == "{{":
            depth_t += 1
            i += 2
            continue
        if two == "}}":
            depth_t = max(0, depth_t - 1)
            i += 2
            continue
        if two == "[[":
            depth_l += 1
            i += 2
            continue
        if two == "]]":
            depth_l = max(0, depth_l - 1)
            i += 2
            continue
        if text[i] == sep and depth_t == 0 and depth_l == 0:
            parts.append(text[last:i])
            last = i + 1
            if sep == "=":  # нужен только первый знак «=»
                break
        i += 1
    parts.append(text[last:])
    return parts


def normalize_key(key: str) -> str:
    return re.sub(r"\s+", "_", key.strip().lower())


def infobox_params(wikitext: str) -> dict[str, str]:
    """Параметры «| ключ = значение» первого инфобокса (сырые значения)."""
    body = find_infobox(_strip_refs(wikitext))
    if body is None:
        return {}
    params: dict[str, str] = {}
    for part in _split_top(body, "|")[1:]:  # [0] — имя шаблона
        kv = _split_top(part, "=")
        if len(kv) < 2:
            continue  # позиционный параметр
        key = normalize_key(kv[0])
        if key and key not in params:
            params[key] = kv[1]
    return params


def _link(m: re.Match) -> str:
    target, _, text = m[1].partition("|")
    if re.match(r"\s*(file|image|category)\s*:", target, re.I):
        return ""
    return (text.rsplit("|", 1)[-1] if text else target).strip()


def _format_date(args: list[str]) -> str:
    nums = [a for a in args if a.isdigit()]
    if len(nums) >= 3:
        return f"{int(nums[2]):02d}.{int(nums[1]):02d}.{nums[0]}"
    if len(nums) == 2:
        return f"{int(nums[1]):02d}.{nums[0]}"
    return nums[0] if nums else ""


def _template(m: re.Match) -> str:
    """Самый внутренний шаблон {{…}} -> текст (неизвестные шаблоны выбрасываются)."""
    parts = [p.strip() for p in m[1].split("|")]
    name = parts[0].lower().replace("_", " ").strip()
    pos = [a for a in parts[1:] if not re.match(r"^[\w\s-]+=", a)]  # без abbr=on и т.п.
    if name in ("convert", "cvt"):  # значение + исходная единица, без пересчёта
        out, i = pos[:1], 1
        while i + 1 < len(pos) and pos[i].lower() in _RANGE_WORDS and re.match(r"^[\d.,]+$", pos[i + 1]):
            word = pos[i].lower()
            out.append("–" if word in ("-", "–", "to") else " × " if word in ("x", "×", "by") else f" {word} ")
            out.append(pos[i + 1])
            i += 2
        unit = f" {pos[i]}" if i < len(pos) else ""
        return "".join(out) + unit
    if name in _LIST_TEMPLATES:
        items = []
        for arg in pos:
            for line in arg.split("\n"):
                line = line.strip().lstrip("*#").strip()
                if line:
                    items.append(line)
        return "; ".join(items)
    if name in _INLINE_TEMPLATES:
        return pos[-1] if name == "lang" and pos else (pos[0] if pos else "")
    if name in _DATE_TEMPLATES:
        return _format_date(pos)
    return ""


def _shorten(text: str, limit: int = MAX_VALUE) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ;,:–-") + "…"


def clean_value(raw: str) -> str:
    """Викиразметка значения -> короткий текст."""
    s = _strip_refs(raw)
    s = re.sub(r"</?br\s*/?>", "; ", s, flags=re.I)
    s = re.sub(r"\[\[File:[^\]]*\]\]", "", s, flags=re.I)
    prev = None
    while prev != s:  # сначала ссылки (в них бывает «|»), потом шаблоны — изнутри наружу
        prev = s
        s = re.sub(r"\[\[([^\[\]]*)\]\]", _link, s)
    s = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", s)  # внешняя ссылка с текстом
    s = re.sub(r"\[https?://\S+\]", "", s)
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\{\{([^{}]*)\}\}", _template, s)
    s = s.replace("{{", "").replace("}}", "")
    s = s.replace("'''", "").replace("''", "")
    s = re.sub(r"<[^>]+>", "", s)  # прочие теги: <sup>, <small> …
    s = html.unescape(s.replace("&nbsp;", " ")).replace("\xa0", " ")
    lines = [ln.strip().lstrip("*#").strip() for ln in s.split("\n")]
    s = "; ".join(ln for ln in lines if ln)
    s = re.sub(r"\(\s*[;,]?\s*\)", "", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*;(\s*;)*\s*", "; ", s)
    s = re.sub(r"\s+([,.:)])", r"\1", s)
    s = s.strip(" ;,")
    return _shorten(s)


def extract_specs(wikitext: str) -> list[list[str]]:
    """Ключевые характеристики из инфобокса: [[подпись, значение], …]."""
    params = infobox_params(wikitext)
    specs: list[list[str]] = []
    for label, keys in SPEC_FIELDS:
        for key in keys:
            value = clean_value(params.get(key, ""))
            if value:
                specs.append([label, value])
                break
        if len(specs) >= MAX_SPECS:
            break
    return specs


def wiki_url(title: str) -> str:
    return "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_"), safe="_()',:!-.")


# ---------- какие товары считаем устройствами ----------

async def accessory_category_ids(conn: aiosqlite.Connection) -> set[int]:
    """Категория «Аксессуары» и все её потомки."""
    async with conn.execute("SELECT id, name, parent_id FROM categories") as cur:
        rows = [tuple(r) for r in await cur.fetchall()]
    ids = {cid for cid, name, _ in rows if name.strip().lower().startswith("аксессуар")}
    grew = True
    while grew:
        children = {cid for cid, _, parent in rows if parent in ids and cid not in ids}
        ids |= children
        grew = bool(children)
    return ids


def device_model(name: str, category_ids: str, accessories: Iterable[int] = ()) -> str:
    """Ключ модели для характеристик или «», если это не устройство."""
    cats = {int(c) for c in (category_ids or "").strip("|").split("|") if c.isdigit()}
    if cats & set(accessories):
        return ""
    model = clean_model(name)
    # без цифр модель неоднозначна: «MacBook Air» — статья обо всех поколениях сразу
    if len(model) < 3 or not re.search(r"\d", model):
        return ""
    return model.lower()


async def load_specs(conn: aiosqlite.Connection, models: Iterable[str] | None = None
                     ) -> dict[str, tuple[list[list[str]], str]]:
    """Найденные характеристики: {модель: (specs, url)}."""
    sql = "SELECT model, specs, url FROM model_specs WHERE specs != '[]'"
    params: list[str] = []
    if models is not None:
        params = list(models)
        if not params:
            return {}
        sql += f" AND model IN ({','.join('?' * len(params))})"
    async with conn.execute(sql, params) as cur:
        rows = await cur.fetchall()
    return {r[0]: (json.loads(r[1]), r[2]) for r in rows}


async def load_model_images(conn: aiosqlite.Connection) -> dict[str, str]:
    """Фото моделей из Википедии: {модель: url}."""
    async with conn.execute("SELECT model, image FROM model_specs WHERE image IS NOT NULL AND image != ''") as cur:
        return {r[0]: r[1] for r in await cur.fetchall()}


# ---------- подбор ----------

class SpecsMatcher:
    def __init__(self, conn: aiosqlite.Connection, *, transport: httpx.AsyncBaseTransport | None = None,
                 min_interval: float = 1.0):
        self.conn = conn
        self.min_interval = min_interval
        self._last = 0.0
        self.offline = False  # Википедия недоступна — прекращаем, промахи не записываем
        self._client = httpx.AsyncClient(timeout=20, headers={"User-Agent": USER_AGENT},
                                         transport=transport, follow_redirects=True)

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, params: dict) -> dict | None:
        wait = self._last + self.min_interval - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        self._last = time.monotonic()
        try:
            resp = await self._client.get(f"{WIKI_API}/w/api.php", params=params)
            if resp.status_code != 200:
                raise httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("Поиск характеристик: %s", exc)
            self.offline = True
            return None

    async def lookup(self, model: str) -> tuple[str, str, list[list[str]]] | None:
        """(заголовок, url, specs) из первой подходящей статьи с инфобоксом."""
        data = await self._get({"action": "query", "list": "search", "srsearch": model,
                                "srlimit": 5, "format": "json"})
        titles = [h.get("title", "") for h in (data or {}).get("query", {}).get("search", [])]
        titles = [t for t in titles if title_matches(model, t)]
        # точное совпадение всех слов модели — вперёд («iPhone 15 Pro» раньше «iPhone 15»)
        want = set(_tokens(model))
        titles.sort(key=lambda t: not want <= set(_tokens(t)))
        for title in titles[:2]:
            page = await self._get({"action": "parse", "page": title, "prop": "wikitext",
                                    "section": 0, "redirects": 1, "format": "json"})
            parsed = (page or {}).get("parse") or {}
            wikitext = parsed.get("wikitext", "")
            if isinstance(wikitext, dict):
                wikitext = wikitext.get("*", "")
            specs = extract_specs(wikitext or "")
            if specs:
                real = parsed.get("title") or title
                return real, wiki_url(real), specs
        return None

    async def page_image(self, title: str) -> str:
        """Главное фото статьи (миниатюра Wikimedia шириной 800)."""
        data = await self._get({"action": "query", "prop": "pageimages", "titles": title,
                                "piprop": "thumbnail", "pithumbsize": 800, "redirects": 1, "format": "json"})
        for page in ((data or {}).get("query", {}).get("pages") or {}).values():
            src = (page.get("thumbnail") or {}).get("source")
            if src:
                return src
        return ""

    async def run(self, limit: int = 60) -> int:
        """Подобрать характеристики моделям без них. Возвращает число найденных моделей."""
        accessories = await accessory_category_ids(self.conn)
        async with self.conn.execute(
            """SELECT name, category_ids FROM products
                WHERE type != 'variation' AND is_active = 1 ORDER BY id DESC"""
        ) as cur:
            products = await cur.fetchall()
        models: dict[str, str] = {}  # ключ -> модель для поиска (как в названии)
        for name, cats in products:
            key = device_model(name, cats, accessories)
            if key and key not in models:
                models[key] = clean_model(name)

        retry_before = (datetime.now(timezone.utc) - RETRY_MISS_AFTER).isoformat(timespec="microseconds")
        async with self.conn.execute("SELECT model, specs, checked_at FROM model_specs") as cur:
            cached = {r[0]: (r[1], r[2]) for r in await cur.fetchall()}
        todo = [k for k in models
                if k not in cached or (cached[k][0] == "[]" and cached[k][1] < retry_before)][:limit]

        found = 0
        for key in todo:
            model = models[key]
            result = await self.lookup(model)
            if self.offline:  # сбой сети — не считаем промахом, повторим в следующий раз
                break
            title, url, specs = result or ("", "", [])
            image = await self.page_image(title) if specs else ""
            if self.offline:
                break
            await self.conn.execute(
                """INSERT INTO model_specs (model, title, url, specs, image, checked_at) VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(model) DO UPDATE SET title = excluded.title, url = excluded.url,
                       specs = excluded.specs, image = excluded.image, checked_at = excluded.checked_at""",
                (key, title, url, json.dumps(specs, ensure_ascii=False), image, utcnow()),
            )
            if specs:
                found += 1
                log.info("Характеристики для «%s»: %s (%d полей)", model, title, len(specs))
            else:
                log.info("Характеристики для «%s» не найдены", model)
        # Фото для моделей, найденных до появления этой функции (image IS NULL)
        if not self.offline and len(todo) < limit:
            async with self.conn.execute(
                "SELECT model, title FROM model_specs WHERE image IS NULL AND title != '' LIMIT ?",
                (limit - len(todo),),
            ) as cur:
                backfill = await cur.fetchall()
            for key, title in backfill:
                image = await self.page_image(title)
                if self.offline:
                    break
                await self.conn.execute("UPDATE model_specs SET image = ? WHERE model = ?", (image, key))
                found += bool(image)
        await self.conn.commit()
        return found


def card_specs(specs: list[list[str]]) -> list[tuple[str, str]]:
    """Ключевые поля для карточки бота в фиксированном порядке."""
    by_label = {label: value for label, value in specs}
    return [(label, by_label[label]) for label in CARD_LABELS if label in by_label]
