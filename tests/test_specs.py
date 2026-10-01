import json
from zoneinfo import ZoneInfo

import pytest

from bot import keyboards as kb
from bot.formatting import MAX_TEXT, product_card
from services.export import build_catalog
from services.specs import card_specs, device_model


def test_device_model():
    assert device_model("iPhone 15 Pro, 256 ГБ, SIM + eSIM", "|15|") == "iphone 15 pro"
    assert device_model("Dyson V15 Detect", "|1|") == "dyson v15 detect"
    assert device_model("AirPods 4 без шумоподавления", "|20|") == "airpods 4"
    assert device_model("iPhone Air, 512 ГБ", "|15|") == "iphone air"          # модели без цифр — тоже
    assert device_model("Чехол iPhone 15 Pro", "|77|", {77}) == ""   # аксессуар


def test_card_specs_order():
    specs = [["Чип", "Apple H2"], ["Автономность", "до 6 ч"], ["Дата выхода", "2023"], ["Вес", "5 г"]]
    assert card_specs(specs) == [("Вес", "5 г"), ("Чип", "Apple H2"), ("Автономность", "до 6 ч")]


# ---------- карточка бота ----------

TZ = ZoneInfo("Europe/Moscow")
PRODUCT = {"name": "iPhone 15 Pro", "permalink": "https://shop/p", "in_stock": 1,
           "price": 10000000, "regular_price": 0}


def test_card_specs_block():
    specs = [["Экран", "6,1″ OLED"], ["Процессор", "Apple A17 Pro"], ["Оперативная память", "8 ГБ"],
             ["Основная камера", "48 Мп"], ["Аккумулятор", "3274 мА·ч"], ["Вес", "187 г"], ["Дата выхода", "2023"]]
    text = product_card(PRODUCT, [], None, TZ, specs=specs)
    block = text.split("<b>Характеристики</b>\n")[1]
    labels = [ln.split(":")[0] for ln in block.split("\n") if ln.startswith("• ")]
    assert labels == ["• Экран", "• Процессор", "• Основная камера", "• Аккумулятор", "• Вес"]
    assert "• Процессор: Apple A17 Pro" in text
    assert "Википеди" not in text
    assert text.index("Характеристики") < text.index("Обновлено")
    assert product_card(PRODUCT, [], None, TZ) == product_card(PRODUCT, [], None, TZ, specs=[])


def test_card_specs_escaped():
    text = product_card(PRODUCT, [], None, TZ, specs=[["Экран", "6.1\" <OLED> & more"]])
    assert "• Экран: 6.1&quot; &lt;OLED&gt; &amp; more" in text


def test_card_drops_specs_before_variants():
    variations = [{"in_stock": 1, "variation_label": f"Вариант номер {i} " + "x" * 40, "name": "v",
                   "price": 100, "regular_price": 0} for i in range(60)]
    specs = [["Экран", "y" * 170], ["Процессор", "z" * 170]]
    # столько вариантов, что без характеристик влезает, а с ними — нет
    n = max(k for k in range(60) if "… и ещё" not in product_card(PRODUCT, variations[:k], None, TZ))
    assert len(product_card(PRODUCT, variations[:n], None, TZ, specs=[])) + 350 > MAX_TEXT
    text = product_card(PRODUCT, variations[:n], None, TZ, specs=specs)
    assert len(text) <= MAX_TEXT and "Характеристики" not in text and "… и ещё" not in text
    text = product_card(PRODUCT, variations, None, TZ, specs=specs)
    assert len(text) <= MAX_TEXT and "Характеристики" not in text and "… и ещё" in text
    short = product_card(PRODUCT, variations[:3], None, TZ, specs=specs)
    assert "Характеристики" in short


SPECS_YAML = """
# тестовый справочник
iPhone:
  iPhone 17 Pro:
    Процессор: Apple A19 Pro
    Вес: 204 г
    Дата выхода: 19.09.2025
Mac:
  MacBook Air 13 M2:
    Другие названия: [MacBook Air 13 Apple M2]
    Экран: 13,6″ Liquid Retina, 2560×1664
    Процессор: Apple M2
  Заготовка без данных:
    Экран:
AirPods:
  AirPods Max USB-C:
    Чип: Apple H1
    Шумоподавление: активное
"""


@pytest.fixture
def specs_book(tmp_path, monkeypatch):
    from services.specs_ref import book
    path = tmp_path / "specs.yaml"
    path.write_text(SPECS_YAML, encoding="utf-8")
    monkeypatch.setattr(book, "path", path)
    monkeypatch.setattr(book, "_mtime", -1.0)
    return book


def test_book_find(specs_book):
    assert specs_book.find("iPhone 17 Pro, 256 ГБ, eSIM")[1][0] == ["Процессор", "Apple A19 Pro"]
    assert specs_book.find("Apple MacBook Air 13 (2022, M2) 8/256 Midnight")[0] == "MacBook Air 13 M2"
    assert specs_book.find("Macbook Air 13 Apple M2 8/256")[0] == "MacBook Air 13 M2"   # другое название
    assert specs_book.find("AirPods Max Type-C")[0] == "AirPods Max USB-C"
    assert specs_book.find("iPhone 17 Pro Max, 256 ГБ") is None                      # другая модель
    assert specs_book.find("Заготовка без данных") is None
    assert "Заготовка без данных" not in specs_book.models()


async def test_catalog_specs_from_book(sync, conn, specs_book):
    await sync.run()
    await conn.execute("INSERT INTO categories (id, name, parent_id, count) VALUES (70, 'Аксессуары', 0, 1)")
    for pid, name, cats in [(9001, "iPhone 17 Pro, 512 ГБ", "|15|"), (9005, "Чехол iPhone 17 Pro", "|70|")]:
        await conn.execute(
            """INSERT INTO products (id, type, name, permalink, price, in_stock, category_ids,
                   first_seen_at, updated_at) VALUES (?, 'simple', ?, 'u', 100, 1, ?, 'x', 'x')""",
            (pid, name, cats))
    await conn.commit()
    catalog = {p["id"]: p for p in (await build_catalog(conn))["products"]}
    assert catalog[9001]["specs"][0] == ["Процессор", "Apple A19 Pro"] and catalog[9001]["year"] == 2025
    assert "specs_src" not in catalog[9001]
    assert "specs" not in catalog[9005]                                            # аксессуар
    json.dumps(catalog)


async def test_bot_card_shows_specs(env, conn, specs_book):
    """Карточка в боте (render_product) показывает характеристики модели."""
    _, click = env
    card = (await click(kb.ProdCb(id=1001, cat=15, page=0))).texts()[0]
    assert "<b>Характеристики</b>\n• Процессор: Apple A19 Pro\n• Вес: 204 г\n" in card
    assert "Википеди" not in card
    assert card.index("114 700 ₽") < card.index("Характеристики") < card.index("Обновлено")
    card = (await click(kb.ProdCb(id=1002, cat=15, page=0))).texts()[0]  # другая модель
    assert "Характеристики" not in card


def test_real_specs_book(caplog):
    """reference/specs.yaml читается без конфликтов и находит модели по названиям с сайта."""
    from services.specs_ref import SpecsBook
    book = SpecsBook()
    names = {
        "MacBook Air 13 (2026,M5) 24/1024 Starlight 10C 10G": "MacBook Air 13 M5",
        "Macbook Air 15 m4 24/512": "MacBook Air 15 M4",
        "MacBook 13 Neo (2026) 8/512 Сitrus": "MacBook Neo",
        "iPhone Air, 512 ГБ": "iPhone Air",
        "iPhone 17 Pro Max, 256 ГБ, eSIM": "iPhone 17 Pro Max",
        "Apple iPad 11 (A16, 2025), 256 ГБ Wi-Fi Yellow": "iPad 11 A16",
        "Apple Watch S11 46mm Rose Gold": "Apple Watch Series 11",
        "Apple Watch Ultra 2 Natural Titanium": "Apple Watch Ultra 2",
        "AirPods Max Type-C": "AirPods Max USB-C",
        "Samsung Galaxy S25 Ultra 12/256": "Samsung Galaxy S25 Ultra",
    }
    for name, model in names.items():
        found = book.find(name)
        assert found and found[0] == model, name
        assert all(label and value for label, value in found[1])
    assert "совпадает" not in caplog.text
