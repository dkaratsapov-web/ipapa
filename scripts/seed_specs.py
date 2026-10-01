"""Разовый черновик справочника характеристик (data/specs.yaml) из Википедии.

Берёт модели устройств из опубликованного каталога, ищет статьи, переводит поля
в понятный вид и пишет specs_seed.json. Бот Википедию не использует — черновик
просматривается и переносится в справочник вручную.
"""
import asyncio
import json
import re
import sys

import httpx

sys.path.insert(0, ".")
from services.images import _OPTIONAL, _tokens, clean_model  # noqa: E402
from services.specs import SpecsMatcher, extract_specs, wiki_url  # noqa: E402
from services.specs_format import humanize  # noqa: E402

CATALOG = "https://raw.githubusercontent.com/dkaratsapov-web/ipapa/webapp-data/catalog.json"
BRANDS = {"apple", "google", "xiaomi", "samsung", "sony", "huawei"}
CHIP = re.compile(r"\b([ams])\s?(\d{1,2})\b")


def relaxed_match(model: str, title: str) -> bool:
    want = [t for t in _tokens(model)]
    while want and want[0] in BRANDS and want[0] not in _tokens(title):
        want = want[1:]
    have = set(_tokens(title.replace("generation", "")))
    if not want or want[0] not in have:
        return False
    missing_nums = [t for t in want if t.isdigit() and t not in have]
    missing = [t for t in want if not t.isdigit() and t not in have]
    if len(missing) > 1 or (missing and missing[0] not in _OPTIONAL | {"a", "m", "s"}):
        return False
    return not missing_nums


def device_models(catalog: dict) -> list[str]:
    cats = {c["id"]: c for c in catalog["categories"]}
    acc = {i for i, c in cats.items() if c["name"].lower().startswith("аксессуар")}
    grew = True
    while grew:
        new = {i for i, c in cats.items() if c.get("parent") in acc and i not in acc}
        acc |= new
        grew = bool(new)
    seen: dict[str, str] = {}
    for p in catalog["products"]:
        if set(p["cats"]) & acc:
            continue
        m = clean_model(p["name"])
        if len(m) >= 3 and m.lower() not in seen:
            seen[m.lower()] = m
    return sorted(seen.values())


async def main() -> None:
    catalog = httpx.get(CATALOG, timeout=60).json()
    models = device_models(catalog)
    print(len(models), "моделей", flush=True)
    matcher = SpecsMatcher(None)  # type: ignore[arg-type]
    out = {}
    for model in models:
        matcher.offline = False
        data = await matcher._get({"action": "query", "list": "search", "srsearch": model,
                                   "srlimit": 6, "format": "json"})
        titles = [h["title"] for h in (data or {}).get("query", {}).get("search", [])]
        good = [t for t in titles if relaxed_match(model, t)]
        want = set(_tokens(model)) - BRANDS
        good.sort(key=lambda t: set(_tokens(t)) - BRANDS != want)  # точное совпадение — первым
        result = None
        for title in good[:2]:
            page = await matcher._get({"action": "parse", "page": title, "prop": "wikitext",
                                       "section": 0, "redirects": 1, "format": "json"})
            parsed = (page or {}).get("parse") or {}
            text = parsed.get("wikitext", "")
            text = text.get("*", "") if isinstance(text, dict) else text
            nice = humanize(extract_specs(text or ""), model)
            if len(nice) >= 3:
                real = parsed.get("title") or title
                result = {"title": real, "url": wiki_url(real), "specs": nice}
                break
        out[model] = result
        print(model, "->", result and result["title"], flush=True)
    await matcher.close()
    json.dump(out, open("specs_seed.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    asyncio.run(main())
