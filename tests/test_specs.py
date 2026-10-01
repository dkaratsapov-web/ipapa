import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest

from bot import keyboards as kb
from bot.formatting import MAX_TEXT, product_card
from services.export import build_catalog
from services.specs import (SpecsMatcher, clean_value, device_model, extract_specs, find_infobox,
                            infobox_params, wiki_url)

IPHONE_15_PRO = """{{Short description|Smartphone made by Apple}}
{{Use mdy dates|date=September 2023}}
{{Infobox mobile phone
| name = iPhone 15 Pro<br />iPhone 15 Pro Max
| logo = IPhone 15 Pro logo.svg
| image = IPhone 15 Pro Natural Titanium.jpg
| caption = iPhone 15 Pro in Natural Titanium
| brand = [[Apple Inc.|Apple]]
| manufacturer = [[Foxconn]]<ref name="foxconn">{{cite web |url=https://example.com/a |title=Foxconn | Apple |date=2023}}</ref>
| series = [[iPhone]]
| first_release = {{Start date and age|2023|09|22}}
| predecessor = [[iPhone 14 Pro]]
| type = [[Smartphone]]
| form = [[Slate phone|Slate]]
| dimensions = {{ubl|'''15 Pro''': H: {{convert|146.6|mm|in|abbr=on}}, W: {{convert|70.6|mm|in|abbr=on}}|'''15 Pro Max''': H: {{convert|159.9|mm|in|abbr=on}}}}
| weight = '''15 Pro''': {{convert|187|g|oz|abbr=on}}<br>'''15 Pro Max''': {{convert|221|g|oz|abbr=on}}<ref>{{cite web|url=https://apple.com|title=Specs}}</ref>
| os = {{plainlist|
* '''Original''': [[iOS 17]]
* '''Current''': [[iOS 18|iOS 18.1]], released {{start date and age|2024|10|28}}
}}
| soc = [[Apple A17|Apple A17 Pro]]<!-- 3 nm -->
| cpu = 6-core (2 performance, 4 efficiency)
| memory = 8&nbsp;[[Gigabyte|GB]] [[LPDDR5]]<ref name="ram" />
| storage = 128&nbsp;GB, 256&nbsp;GB, 512&nbsp;GB, 1&nbsp;TB
| battery = '''15 Pro''': 3274&nbsp;[[Milliampere-hour|mAh]]<br/>'''15 Pro Max''': 4422&nbsp;mAh
| charging = [[MagSafe (Apple)|MagSafe]], [[Qi (standard)|Qi2]] wireless charging, [[USB-C]] (USB 3, up to 27&nbsp;W)
| display = {{nowrap|'''15 Pro''': {{convert|6.1|in|mm|abbr=on}}}} [[OLED]] Super Retina XDR, 2556×1179 px, 460&nbsp;ppi, [[ProMotion]] 120&nbsp;Hz
| rear_camera = 48&nbsp;MP main, 12&nbsp;MP ultra-wide, 12&nbsp;MP 3× telephoto {{small|(5× on Pro Max)}}
| front_camera = 12&nbsp;MP TrueDepth, ''f''/1.9
| water_resistance = [[IP code|IP68]] (6&nbsp;m for 30 minutes)
| website = {{URL|apple.com/iphone-15-pro}}
}}
'''iPhone 15 Pro''' and '''iPhone 15 Pro Max''' are [[smartphone]]s designed by [[Apple Inc.]]
{{Infobox other|display = must not be used}}
"""

MACBOOK_AIR_M2 = """{{Infobox information appliance
| name         = MacBook Air (M2, 2022)
| developer    = [[Apple Inc.]]
| type         = [[Laptop|Notebook]]
| releasedate  = {{start date|2022|07|15}}
| discontinued =
| os           = [[macOS Monterey]]<br />[[macOS Ventura]] and later
| cpu          = [[Apple M2]] (8-core)<ref>{{Cite web |title=MacBook Air (M2, 2022) - Tech Specs |url=https://support.apple.com/kb/SP869}}</ref>
| memory       = 8, 16 or 24&nbsp;GB unified [[LPDDR5]]
| storage      = 256&nbsp;GB – 2&nbsp;TB [[Solid-state drive|SSD]]
| display      = {{convert|13.6|in|cm|abbr=on}} [[Liquid Retina]] [[IPS panel|IPS]] LCD, 2560×1664
| camera       = 1080p FaceTime HD
| power        = 52.6&nbsp;W·h [[Lithium polymer battery|lithium-polymer]]
| dimensions   = {{convert|30.41|x|21.5|x|1.13|cm|in|abbr=on}}
| weight       = {{cvt|1.24|kg|lb}}
| predecessor  = [[MacBook Air (Apple silicon)|MacBook Air (M1, 2020)]]
}}
The '''MacBook Air''' is a line of laptops.
"""

NO_INFOBOX = "'''DJI''' is a Chinese technology company.<ref>x</ref>"


# ---------- разбор ----------

def test_find_infobox_balanced():
    body = find_infobox(IPHONE_15_PRO)
    assert body.startswith("Infobox mobile phone")
    assert body.rstrip().endswith("{{URL|apple.com/iphone-15-pro}}")  # вложенные }} не обрывают шаблон
    assert find_infobox(NO_INFOBOX) is None
    assert find_infobox("{{Infobox phone | a = {{b}}") is None  # не закрыт


def test_infobox_params_nested_pipes():
    params = infobox_params(IPHONE_15_PRO)
    # «|» внутри ссылок, шаблонов и <ref> не режет параметры
    assert params["brand"].strip() == "[[Apple Inc.|Apple]]"
    assert params["manufacturer"].strip() == "[[Foxconn]]"
    assert "15 Pro Max" in params["dimensions"]
    assert "display" in params and "must not be used" not in params["display"]  # второй инфобокс не берём
    assert {k: v.strip() for k, v in infobox_params("{{Infobox x\n| Release Date = 2020\n}}").items()} \
        == {"release_date": "2020"}


@pytest.mark.parametrize("raw, clean", [
    ("[[Apple A17|Apple A17 Pro]]<!-- 3 nm -->", "Apple A17 Pro"),
    ("8&nbsp;[[Gigabyte|GB]] [[LPDDR5]]<ref name=\"ram\" />", "8 GB LPDDR5"),
    ("{{convert|6.1|in|mm|abbr=on}} OLED", "6.1 in OLED"),
    ("{{convert|30.41|x|21.5|x|1.13|cm|in}}", "30.41 × 21.5 × 1.13 cm"),
    ("{{convert|6|to|8|in|mm}}", "6–8 in"),
    ("a<br>b<br/>c<br />d</br>e", "a; b; c; d; e"),
    ("{{ubl|one|two|class=x}}", "one; two"),
    ("{{Unbulleted list|[[iOS 17]]|[[iOS 18|iOS 18.1]]}}", "iOS 17; iOS 18.1"),
    ("{{plainlist|\n* first\n* second [[x|y]]\n}}", "first; second y"),
    ("{{flatlist|\n* A\n* B\n}}", "A; B"),
    ("{{hlist|A|B}}", "A; B"),
    ("{{nowrap|12 MP}}, {{nobr|f/1.9}} {{small|(wide)}}", "12 MP, f/1.9 (wide)"),
    ("IP68 {{citation needed|date=May 2024}}", "IP68"),
    ("'''15 Pro''': 187 g", "15 Pro: 187 g"),
    ("{{Start date and age|2023|09|22}}", "22.09.2023"),
    ("x<ref>{{cite web|url=a|title=b}}</ref> y", "x y"),
    ("[[File:Logo.svg|20px|alt]] Text", "Text"),
    ("", ""),
    ("{{cite web|url=x}}", ""),
])
def test_clean_value(raw, clean):
    assert clean_value(raw) == clean


def test_clean_value_caps_length():
    value = clean_value("word " * 100)
    assert len(value) <= 180 and value.endswith("word…")


def test_extract_specs_phone():
    specs = extract_specs(IPHONE_15_PRO)
    d = dict(specs)
    assert [label for label, _ in specs][:3] == ["Экран", "Процессор", "Оперативная память"]
    assert len(specs) == 12  # все 12 полей, включая «Вес» и «Дату выхода»
    assert d["Экран"].startswith("15 Pro: 6.1 in OLED Super Retina XDR, 2556×1179 px")
    assert d["Процессор"] == "Apple A17 Pro"                     # soc раньше cpu
    assert d["Оперативная память"] == "8 GB LPDDR5"
    assert d["Основная камера"].endswith("3× telephoto (5× on Pro Max)")
    assert d["Фронтальная камера"] == "12 MP TrueDepth, f/1.9"
    assert d["Аккумулятор"] == "15 Pro: 3274 mAh; 15 Pro Max: 4422 mAh"
    assert d["Зарядка"].startswith("MagSafe, Qi2 wireless charging, USB-C")
    assert d["Влагозащита"] == "IP68 (6 m for 30 minutes)"
    assert d["ОС"] == "Original: iOS 17; Current: iOS 18.1, released 28.10.2024"
    assert d["Размеры"] == "15 Pro: H: 146.6 mm, W: 70.6 mm; 15 Pro Max: H: 159.9 mm"
    for _, value in specs:
        assert "{{" not in value and "[[" not in value and "<" not in value and "&nbsp;" not in value


def test_extract_specs_laptop():
    d = dict(extract_specs(MACBOOK_AIR_M2))
    assert d["Экран"] == "13.6 in Liquid Retina IPS LCD, 2560×1664"
    assert d["Процессор"] == "Apple M2 (8-core)"
    assert d["Оперативная память"] == "8, 16 or 24 GB unified LPDDR5"
    assert d["Основная камера"] == "1080p FaceTime HD"
    assert d["Аккумулятор"] == "52.6 W·h lithium-polymer"            # power
    assert d["ОС"] == "macOS Monterey; macOS Ventura and later"
    assert d["Вес"] == "1.24 kg"
    assert d["Размеры"] == "30.41 × 21.5 × 1.13 cm"
    assert d["Дата выхода"] == "15.07.2022"
    assert extract_specs(NO_INFOBOX) == []


def test_wiki_url():
    assert wiki_url("iPhone 15 Pro") == "https://en.wikipedia.org/wiki/iPhone_15_Pro"
    assert wiki_url("MacBook Air (Apple silicon)") == "https://en.wikipedia.org/wiki/MacBook_Air_(Apple_silicon)"


def test_device_model():
    assert device_model("iPhone 15 Pro, 256 ГБ, SIM + eSIM", "|15|") == "iphone 15 pro"
    assert device_model("Dyson V15 Detect", "|1|") == "dyson v15 detect"
    assert device_model("AirPods 4 без шумоподавления", "|20|") == "airpods 4"
    assert device_model("Чехол iPhone 15 Pro", "|77|", {77}) == ""   # аксессуар
    assert device_model("Apple Pencil", "|1|") == ""                   # без цифр — неоднозначно


# ---------- подбор ----------

class Wiki:
    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.pages = {"iPhone 15 Pro": IPHONE_15_PRO, "MacBook Air (Apple silicon)": MACBOOK_AIR_M2,
                      "DJI": NO_INFOBOX}
        self.search = {"iPhone 15 Pro": ["iPhone 15", "iPhone 15 Pro"],
                       "MacBook Air 13": ["MacBook Air 13-inch"],
                       "DJI Ronin RSC 2": ["DJI"]}
        self.redirects = {"MacBook Air 13-inch": "MacBook Air (Apple silicon)"}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        p = request.url.params
        assert request.headers["user-agent"].startswith("IPapaPriceBot/1.0")
        if request.url.path != "/w/api.php":
            return httpx.Response(404)
        if p.get("list") == "search":
            return httpx.Response(200, json={"query": {"search": [
                {"title": t} for t in self.search.get(p["srsearch"], [])]}})
        if p.get("action") == "parse":
            assert p["prop"] == "wikitext" and p["section"] == "0" and p["redirects"] == "1"
            title = self.redirects.get(p["page"], p["page"])
            if title not in self.pages:
                return httpx.Response(200, json={"error": {"code": "missingtitle"}})
            return httpx.Response(200, json={"parse": {"title": title, "wikitext": {"*": self.pages[title]}}})
        if p.get("prop") == "pageimages":
            title = p["titles"]
            thumb = {"source": f"https://upload.wikimedia.org/thumb/{title.replace(' ', '_')}.jpg/800px-x.jpg"}
            return httpx.Response(200, json={"query": {"pages": {"1": {"title": title, "thumbnail": thumb}}}})
        return httpx.Response(400)

    def searched(self) -> list[str]:
        return [r.url.params["srsearch"] for r in self.requests if r.url.params.get("list") == "search"]


async def add_products(conn):
    await conn.execute("INSERT INTO categories (id, name, parent_id, count) VALUES (70, 'Аксессуары', 0, 1)")
    await conn.execute("INSERT INTO categories (id, name, parent_id, count) VALUES (71, 'Чехлы', 70, 1)")
    items = [
        (9001, "iPhone 15 Pro, 256 ГБ, SIM + eSIM", "|15|"),
        (9002, "iPhone 15 Pro, 128 ГБ, eSIM", "|15|"),                 # та же модель
        (9003, "MacBook Air 13 M2/8/256GB Midnight", "|50|"),
        (9004, "Стабилизатор DJI Ronin RSC 2", "|60|"),                # статьи с инфобоксом нет
        (9005, "Чехол iPhone 15 Pro MagSafe", "|71|"),                  # аксессуар
        (9006, "Apple Pencil", "|60|"),                                 # без цифр
    ]
    for pid, name, cats in items:
        await conn.execute(
            """INSERT INTO products (id, type, name, permalink, price, in_stock, category_ids,
                   first_seen_at, updated_at) VALUES (?, 'simple', ?, 'u', 100, 1, ?, 'x', 'x')""",
            (pid, name, cats))
    await conn.commit()


async def test_matcher(sync, conn, repo):
    await sync.run()
    await add_products(conn)
    wiki = Wiki()
    matcher = SpecsMatcher(conn, transport=httpx.MockTransport(wiki.handler), min_interval=0)
    assert await matcher.run() == 2
    searched = wiki.searched()
    assert searched.count("iPhone 15 Pro") == 1                        # один запрос на модель
    assert "MacBook Air 13" in searched and "DJI Ronin RSC 2" in searched
    assert not any("Pencil" in s or "Чехол" in s for s in searched)
    # «iPhone 15 Pro» раньше «iPhone 15», хотя поиск вернул его вторым
    parsed = [r.url.params["page"] for r in wiki.requests if r.url.params.get("action") == "parse"]
    assert "iPhone 15 Pro" in parsed and "iPhone 15" not in parsed

    specs, url = await repo.specs_for_model("iPhone 15 Pro")
    assert url == "https://en.wikipedia.org/wiki/iPhone_15_Pro" and dict(specs)["Процессор"] == "Apple A17 Pro"
    _, url = await repo.specs_for_model("macbook air 13")
    assert url == "https://en.wikipedia.org/wiki/MacBook_Air_(Apple_silicon)"   # после редиректа

    # фото модели из статьи — дополнительное фото в галерее товара с одним фото
    from services.specs import load_model_images
    images = await load_model_images(conn)
    assert images["iphone 15 pro"].endswith("800px-x.jpg")
    assert await repo.specs_for_model("dji ronin rsc 2") is None                  # промах
    assert await repo.specs_for_product(await repo.get_product(9005)) is None     # аксессуар

    # кэш: повторный запуск ничего не спрашивает
    wiki.requests.clear()
    assert await matcher.run() == 0 and wiki.requests == []

    # промах перепроверяется через 7 дней, найденное — нет
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(timespec="microseconds")
    await conn.execute("UPDATE model_specs SET checked_at = ?", (old,))
    await conn.commit()
    wiki.pages["DJI Ronin RSC 2"] = MACBOOK_AIR_M2
    wiki.search["DJI Ronin RSC 2"] = ["DJI Ronin RSC 2"]
    assert await matcher.run() == 1
    searched = wiki.searched()
    assert "DJI Ronin RSC 2" in searched                                     # промах — ещё раз
    assert "iPhone 15 Pro" not in searched and "MacBook Air 13" not in searched  # найденное — нет
    await matcher.close()

    catalog = {p["id"]: p for p in (await build_catalog(conn))["products"]}
    assert catalog[9001]["specs_src"] == "https://en.wikipedia.org/wiki/iPhone_15_Pro"
    assert catalog[9001]["specs"] == catalog[9002]["specs"]
    assert ["Процессор", "Apple A17 Pro"] in catalog[9001]["specs"]
    assert "specs" not in catalog[9005] and "specs_src" not in catalog[9005]   # чехол
    assert "specs" not in catalog[9006]
    assert "specs" not in catalog[1001]                                        # не искали
    json.dumps(catalog)


async def test_matcher_network_error(sync, conn):
    await sync.run()

    calls = []

    def boom(request):
        calls.append(request)
        raise httpx.ConnectError("blocked")
    matcher = SpecsMatcher(conn, transport=httpx.MockTransport(boom), min_interval=0)
    assert await matcher.run() == 0
    await matcher.close()
    assert len(calls) == 1                     # после первого сбоя дальше не идём
    async with conn.execute("SELECT COUNT(*) FROM model_specs") as cur:
        assert (await cur.fetchone())[0] == 0  # сбой сети — не промах, повторим при следующей синхронизации


# ---------- карточка бота ----------

TZ = ZoneInfo("Europe/Moscow")
PRODUCT = {"name": "iPhone 15 Pro", "permalink": "https://shop/p", "in_stock": 1,
           "price": 10000000, "regular_price": 0}


def test_card_specs_block():
    specs = extract_specs(IPHONE_15_PRO) + [["Экран", "<b>x</b>"]]
    text = product_card(PRODUCT, [], None, TZ, specs=specs,
                        specs_url="https://en.wikipedia.org/wiki/iPhone_15_Pro")
    block = text.split("<b>Характеристики</b>\n")[1]
    labels = [ln.split(":")[0] for ln in block.split("\n") if ln.startswith("• ")]
    assert labels == ["• Экран", "• Процессор", "• Основная камера", "• Аккумулятор", "• Вес"]
    assert "• Процессор: Apple A17 Pro" in text
    assert '<a href="https://en.wikipedia.org/wiki/iPhone_15_Pro">По данным Википедии</a>' in text
    assert text.index("Характеристики") < text.index("Обновлено")
    assert product_card(PRODUCT, [], None, TZ) == product_card(PRODUCT, [], None, TZ, specs=[])


def test_card_specs_escaped():
    text = product_card(PRODUCT, [], None, TZ, specs=[["Экран", "6.1\" <OLED> & more"]], specs_url="u")
    assert "• Экран: 6.1&quot; &lt;OLED&gt; &amp; more" in text


def test_card_drops_specs_before_variants():
    variations = [{"in_stock": 1, "variation_label": f"Вариант номер {i} " + "x" * 40, "name": "v",
                   "price": 100, "regular_price": 0} for i in range(60)]
    specs = [["Экран", "y" * 170], ["Процессор", "z" * 170]]
    # столько вариантов, что без характеристик влезает, а с ними — нет
    n = max(k for k in range(60) if "… и ещё" not in product_card(PRODUCT, variations[:k], None, TZ))
    assert len(product_card(PRODUCT, variations[:n], None, TZ, specs=[], specs_url="u")) + 350 > MAX_TEXT
    text = product_card(PRODUCT, variations[:n], None, TZ, specs=specs, specs_url="u")
    assert len(text) <= MAX_TEXT and "Характеристики" not in text and "… и ещё" not in text
    text = product_card(PRODUCT, variations, None, TZ, specs=specs, specs_url="u")
    assert len(text) <= MAX_TEXT and "Характеристики" not in text and "… и ещё" in text
    short = product_card(PRODUCT, variations[:3], None, TZ, specs=specs, specs_url="u")
    assert "Характеристики" in short


async def test_bot_card_shows_specs(env, conn):
    """Карточка в боте (render_product) показывает характеристики модели."""
    _, click = env
    await conn.execute(
        "INSERT INTO model_specs (model, title, url, specs, checked_at) VALUES (?, ?, ?, ?, 'x')",
        ("iphone 17 pro", "iPhone 17 Pro", "https://en.wikipedia.org/wiki/iPhone_17_Pro",
         json.dumps([["Процессор", "Apple A19 Pro"], ["ОС", "iOS 26"], ["Вес", "204 g"]])))
    await conn.commit()
    card = (await click(kb.ProdCb(id=1001, cat=15, page=0))).texts()[0]
    assert "<b>Характеристики</b>\n• Процессор: Apple A19 Pro\n• Вес: 204 g\n" in card
    assert '<a href="https://en.wikipedia.org/wiki/iPhone_17_Pro">По данным Википедии</a>' in card
    assert card.index("114 700 ₽") < card.index("Характеристики") < card.index("Обновлено")
    card = (await click(kb.ProdCb(id=1002, cat=15, page=0))).texts()[0]  # другая модель
    assert "Характеристики" not in card
