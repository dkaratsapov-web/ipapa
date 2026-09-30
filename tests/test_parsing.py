import pytest

from services.parsing import (format_diff, format_price, parse_price, parse_product,
                              parse_variation_label, search_terms, short_label)
from tests.conftest import load_fixture


@pytest.mark.parametrize("raw, minor, expected", [
    ("11470000", 2, 11470000),   # 114 700 ₽ в копейках
    ("114700", 0, 11470000),
    ("0", 2, 0),
    ("", 2, 0),
    (None, 2, 0),
    ("1147000", 1, 11470000),
    ("114700000", 3, 11470000),
])
def test_parse_price(raw, minor, expected):
    assert parse_price(raw, minor) == expected


@pytest.mark.parametrize("kop, text", [
    (11470000, "114 700 ₽"),
    (99000, "990 ₽"),
    (123456789, "1 234 567,89 ₽"),
    (0, "Цена по запросу"),
])
def test_format_price(kop, text):
    assert format_price(kop) == text


def test_format_diff():
    assert format_diff(-500000) == "−5 000 ₽"
    assert format_diff(100000) == "+1 000 ₽"


def test_variation_label():
    raw = "Память: 2 ТБ, Цвет: Silver, Количество сим-карт: eSIM"
    assert parse_variation_label(raw) == raw
    assert short_label(raw) == "2 ТБ · Silver · eSIM"
    assert parse_variation_label([{"attribute": "Цвет", "value": "Silver"}]) == "Цвет: Silver"
    assert parse_variation_label("") == ""


def test_search_terms():
    assert search_terms("  iPhone 17 PRO,  256 ") == ["iphone", "17", "pro", "256"]
    assert search_terms("Чёрный") == ["черный"]


def test_parse_product_from_fixture():
    variations = {v["id"]: parse_product(v) for v in load_fixture("variations")}
    products = {p["id"]: parse_product(p) for p in load_fixture("products")}

    v = variations[5001]
    assert v.type == "variation" and v.parent_id == 1001
    assert v.price == 11470000 and format_price(v.price) == "114 700 ₽"
    assert v.in_stock is True
    assert short_label(v.variation_label) == "256 ГБ · Silver · eSIM"

    sale = variations[5004]
    assert sale.regular_price > sale.price

    airpods = products[2001]
    assert airpods.type == "simple"
    assert airpods.regular_price == 2499000 and airpods.sale_price == airpods.price == 2199000
    assert airpods.image_url.endswith(".jpg")
    assert airpods.category_ids == [20]

    assert products[4001].price == 0  # цена по запросу
