import json

import httpx
import pytest

from services.export import build_catalog
from services.images import ImageMatcher, clean_model, resize_wiki_thumb, title_matches


@pytest.mark.parametrize("name, model", [
    ("iPhone 15 Pro Max, 256 ГБ, SIM + eSIM", "iPhone 15 Pro Max"),
    ("iPad 9-поколения Space Gray 64GB Wi-Fi", "iPad 9"),
    ("AirPods 4 без шумоподавления", "AirPods 4"),
    ("Apple Watch SE 3 Starlight 44mm", "Apple Watch SE 3"),
    ("Apple Watch S9 41mm Midnight", "Apple Watch Series 9"),
    ("Samsung Galaxy S26, 12/256 ГБ, SIM + eSIM", "Samsung Galaxy S26"),
    ("MacBook Pro 13″ (2020) M1/8/256GB Space Gray", "MacBook Pro 13 M1"),
    ("iPad Mini 6 2021 Sapce Gray 64GB Wi-Fi+Sim", "iPad Mini 6"),
    ("Стабилизатор DJI Ronin RSC 2", "DJI Ronin RSC 2"),
])
def test_clean_model(name, model):
    assert clean_model(name) == model


def test_title_matches():
    assert title_matches("iPhone 15 Pro Max", "iPhone 15 Pro")
    assert title_matches("iPad 9", "iPad (9th generation)")
    assert not title_matches("iPhone 15", "iPhone 13")            # чужая модель
    assert not title_matches("Samsung Galaxy S26", "Samsung Galaxy S25")
    assert not title_matches("iPhone 15", "Apple Inc.")


def test_resize_thumb():
    url = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/X.jpg/320px-X.jpg"
    assert resize_wiki_thumb(url, 800).endswith("/800px-X.jpg")


def wiki_handler(requests):
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/w/api.php":
            q = request.url.params["srsearch"]
            hits = {"iPhone 13": ["iPhone 13 Pro", "iPhone 13"], "DJI Ronin RSC 2": ["DJI"]}.get(q, [])
            return httpx.Response(200, json={"query": {"search": [{"title": t} for t in hits]}})
        if request.url.path.startswith("/api/rest_v1/page/summary/"):
            return httpx.Response(200, json={"thumbnail": {
                "source": "https://upload.wikimedia.org/x/thumb/a/b/I.jpg/320px-I.jpg"}})
        return httpx.Response(404)
    return handler


async def test_matcher(sync, conn, repo):
    await sync.run()
    # три «Б/У» товара без фото
    for pid, name in [(9001, "iPhone 17 Pro, 256 ГБ, eSIM"),     # есть новый iPhone 17 Pro в каталоге
                      (9002, "iPhone 13, 128 ГБ, SIM + eSIM"),   # найдётся в Википедии
                      (9003, "Стабилизатор DJI Ronin RSC 2")]:    # не найдётся
        await conn.execute(
            """INSERT INTO products (id, type, name, permalink, price, in_stock, category_ids,
                   first_seen_at, updated_at) VALUES (?, 'simple', ?, 'u', 100, 1, '|212|', 'x', 'x')""",
            (pid, name))
    await conn.commit()

    requests = []
    matcher = ImageMatcher(conn, transport=httpx.MockTransport(wiki_handler(requests)), min_interval=0)
    assert await matcher.run() == 2
    # повторный запуск ничего не ищет: результаты в кэше, промах перепроверится через неделю
    requests.clear()
    assert await matcher.run() == 0 and requests == []
    await matcher.close()

    p1 = await repo.get_product(9001)
    assert p1["image_url"].endswith("iphone-17-pro.jpg")        # из своего каталога
    p2 = await repo.get_product(9002)
    assert p2["image_url"].endswith("/800px-I.jpg")             # из Википедии
    assert (await repo.get_product(9003))["image_url"] == ""

    catalog = {p["id"]: p for p in (await build_catalog(conn))["products"]}
    assert catalog[9002]["img"].endswith("/800px-I.jpg") and catalog[9002]["thumb"].endswith("/300px-I.jpg")
    json.dumps(catalog)
