import json
import os

import httpx
from aiogram.methods import SendMessage

from bot.handlers.webapp import build_router as webapp_router  # noqa: F401 — импорт проверяет связность
from services import leads, tradein
from services.api_client import StoreApiClient
from tests.conftest import FIXTURES
from tests.test_bot_smoke import ADMIN, USER  # noqa: F401

PAGE = open(os.path.join(FIXTURES, "real", "trade-in.html"), encoding="utf-8").read()


def test_parse_tradein_page():
    data = tradein.parse_tradein_page(PAGE)
    assert [c["id"] for c in data["conditions"]] == ["pristine", "light", "visible", "heavy"]
    slugs = [d["slug"] for d in data["devices"]]
    assert slugs == ["iphone", "ipad", "watch"]
    iphone = data["devices"][0]
    se = iphone["models"][0]
    assert se["id"] == "se-2022" and se["variants"][0] == {
        "id": "64", "label": "64 ГБ", "prices": {"pristine": 5000, "light": 4250, "visible": 3250, "heavy": 2250}}
    assert tradein.parse_tradein_page("<html>нет калькулятора</html>") is None


def test_tradein_estimate():
    data = tradein.parse_tradein_page(PAGE)
    model, variant, cond, price = leads.tradein_estimate(data, "se-2022", "128", "light")
    assert (model, variant, cond, price) == ("iPhone SE(2022)", "128 ГБ", "Незначительные повреждения", 5100)
    assert leads.tradein_estimate(data, "nope", "1", "light") is None


def test_deep_link_codes():
    assert leads.from_deep_link("o5885-1_5001-2").data == {"items": [[5885, 1], [5001, 2]]}
    r = leads.from_deep_link("r0_2")
    assert r.kind == "repair" and r.data == {"device": "Телефон", "problem": "Попала вода"}
    assert leads.from_deep_link("r9_9") is None
    t = leads.from_deep_link("t~se-2022~64~pristine", tradein.parse_tradein_page(PAGE))
    assert t.data["estimate"] == 5000 and t.data["model"] == "iPhone SE(2022)"
    assert leads.from_deep_link("s5001") is None  # это подписка, не заявка


def test_from_web_app():
    lead = leads.from_web_app({"a": "lead", "kind": "repair", "device": "Телефон", "model": "iPhone 13",
                               "problem": "Разбит экран", "name": "Иван", "phone": "+7 (900) 013-14-15"})
    assert lead.phone == "+79000131415" and lead.data["model"] == "iPhone 13"
    assert leads.from_web_app({"a": "lead", "kind": "order", "items": []}) is None
    assert leads.from_web_app({"a": "lead", "kind": "hack"}) is None


async def test_refresh_keeps_old_on_failure(conn):
    def handler(request):
        return httpx.Response(200, text=PAGE)
    api = StoreApiClient("https://shop.test/wp-json/wc/store/v1", min_interval=0, backoff=0,
                         transport=httpx.MockTransport(handler))
    assert await tradein.refresh(conn, api, "https://shop.test")
    await api.close()
    broken = StoreApiClient("https://shop.test", min_interval=0, backoff=0, retries=1,
                            transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    assert not await tradein.refresh(conn, broken, "https://shop.test")
    await broken.close()
    assert (await tradein.load(conn))["devices"][0]["slug"] == "iphone"


async def test_lead_flow_in_bot(env, repo, conn):
    send_text, _ = env
    # заказ из мини-аппа (sendData)
    payload = {"a": "lead", "kind": "order", "items": [[5001, 2], [2001, 1]], "name": "Иван", "phone": "89000131415"}
    s = await send_text("", web_app_data=json.dumps(payload))
    sent = [c for c in s.calls if isinstance(c, SendMessage)]
    manager = next(c for c in sent if c.chat_id == ADMIN)
    assert "Заказ" in manager.text and "№1" in manager.text and "× 2" in manager.text and "89000131415" in manager.text
    client = next(c for c in sent if c.chat_id == USER)
    assert "Заявка №1 принята" in client.text and "Итого" in client.text

    # ремонт по deep link без телефона — просим номер
    s = await send_text("/start r0_0")
    client = [c for c in s.calls if isinstance(c, SendMessage) and c.chat_id == USER][-1]
    assert "Разбит экран" in client.text and client.reply_markup.keyboard[0][0].request_contact

    # клиент отправил контакт — телефон уходит менеджерам
    s = await send_text("", contact="+7 900 013 14 15")
    manager = next(c for c in s.calls if isinstance(c, SendMessage) and c.chat_id == ADMIN)
    assert "№2" in manager.text and "+79000131415" in manager.text
    rows = await leads.recent(conn)
    assert [r["kind"] for r in rows] == ["repair", "order"] and rows[0]["phone"] == "+79000131415"

    s = await send_text("/leads", ADMIN)
    assert "№2" in s.texts()[0] and "Ремонт" in s.texts()[0]


async def test_tradein_in_export(conn):
    from services.export import build_catalog
    api = StoreApiClient("https://shop.test/wp-json/wc/store/v1", min_interval=0, backoff=0,
                         transport=httpx.MockTransport(lambda r: httpx.Response(200, text=PAGE)))
    assert "tradein" not in await build_catalog(conn)
    await tradein.refresh(conn, api, "https://shop.test")
    await api.close()
    catalog = await build_catalog(conn)
    assert catalog["tradein"]["conditions"][0]["id"] == "pristine"
