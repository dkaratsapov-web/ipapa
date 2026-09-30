from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage

from services.notifier import Notifier
from services.reports import changes_report, daily_digest

TZ = ZoneInfo("Europe/Moscow")


class FakeBot:
    def __init__(self, blocked: set[int] = frozenset()):
        self.sent: list[tuple[int, str]] = []
        self.blocked = blocked

    async def send_message(self, chat_id, text, **kwargs):
        if chat_id in self.blocked:
            raise TelegramForbiddenError(method=SendMessage(chat_id=chat_id, text=text),
                                         message="Forbidden: bot was blocked by the user")
        self.sent.append((chat_id, text))


async def price_of(conn, pid):
    async with conn.execute("SELECT price, in_stock, is_active FROM products WHERE id = ?", (pid,)) as cur:
        return tuple(await cur.fetchone())


async def history_count(conn):
    async with conn.execute("SELECT COUNT(*) FROM price_history") as cur:
        return (await cur.fetchone())[0]


async def test_first_sync_loads_everything(sync, site, conn, repo):
    result = await sync.run()
    assert result.ok, result.error
    assert result.first_sync
    assert result.products_count == result.products_total == len(site.products)
    assert result.variations_count == result.variations_total == len(site.variations)
    assert result.categories_count == len(site.categories)
    # per_page=3 -> несколько страниц
    assert len(site.requests) > 3
    # первая синхронизация не создаёт событий
    assert await history_count(conn) == 0
    assert result.price_changes == 0
    assert await price_of(conn, 5001) == (11470000, 1, 1)
    last = await repo.last_sync("success")
    assert last["products_count"] == len(site.products)


async def test_price_change_emulated_in_db_notifies_subscriber(sync, conn, repo):
    await sync.run()
    await repo.upsert_user(10, "alice", False)
    await repo.upsert_user(20, "bob", False)
    await repo.upsert_user(30, "eve", False)
    await repo.add_subscription(10, 1001)   # весь товар
    await repo.add_subscription(20, 5001)   # конкретный вариант
    await repo.add_subscription(30, 5002)   # другой вариант — не должен получить

    # Эмулируем «старую» цену в базе: на сайте 114 700, у нас было 119 700
    await conn.execute("UPDATE products SET price = 11970000 WHERE id = 5001")
    # и отсутствие в наличии у другого варианта
    await conn.execute("UPDATE products SET in_stock = 0 WHERE id = 5004")
    await conn.commit()

    result = await sync.run()
    assert result.ok
    assert result.price_changes == 1 and result.stock_changes == 1
    assert await history_count(conn) == 2

    bot = FakeBot()
    sent = await Notifier(bot, repo, delay=0).process_queue()
    recipients = sorted(chat for chat, _ in bot.sent)
    assert recipients == [10, 10, 20]   # alice: цена + наличие, bob: цена
    text = next(t for chat, t in bot.sent if chat == 20)
    assert "iPhone 17 Pro 256 ГБ · Silver · eSIM" in text
    assert "119 700 ₽ → <b>114 700 ₽</b> (−5 000 ₽)" in text
    assert sent == 3

    # очередь обработана — повторно не шлём
    assert await Notifier(bot, repo, delay=0).process_queue() == 0

    report = "\n".join(await changes_report(repo, 24, TZ))
    assert "119 700 ₽ → <b>114 700 ₽</b>" in report
    digest = "\n".join(await daily_digest(repo, TZ))
    assert "Изменений цен: 1" in digest


async def test_blocked_user_marked_inactive(sync, conn, repo):
    await sync.run()
    await repo.upsert_user(10, "alice", False)
    await repo.add_subscription(10, 5001)
    await conn.execute("UPDATE products SET price = 11970000 WHERE id = 5001")
    await conn.commit()
    await sync.run()
    await Notifier(FakeBot(blocked={10}), repo, delay=0).process_queue()
    assert await repo.count_users() == (1, 0)


async def test_api_error_does_not_touch_db(sync, site, conn, repo):
    await sync.run()
    await conn.execute("UPDATE products SET price = 1 WHERE id = 5001")
    await conn.commit()
    site.fail_status = 500
    site.fail_on = "variation"
    site.requests.clear()

    result = await sync.run()
    assert not result.ok
    assert "500" in result.error
    # 3 попытки на упавший запрос
    failed = [r for r in site.requests if r.url.params.get("type") == "variation"]
    assert len(failed) == 3
    assert await price_of(conn, 5001) == (1, 1, 1)   # не перезаписано
    assert await history_count(conn) == 0
    assert (await repo.last_sync())["status"] == "failed"


async def test_shrunk_response_is_rejected(sync, site, conn, repo):
    await sync.run()
    site.products = site.products[:2]   # меньше 50% от прошлого
    result = await sync.run()
    assert not result.ok
    assert "50%" in result.error
    assert await price_of(conn, 3001) == (9990000, 0, 1)  # не деактивирован
    assert (await repo.last_sync("success"))["products_count"] == 6


async def test_empty_first_sync_rejected(sync, site, repo):
    site.products = []
    result = await sync.run()
    assert not result.ok
    assert await repo.top_categories() == []


async def test_missing_product_deactivated_and_new_detected(sync, site, conn, repo):
    await sync.run()
    removed = site.products.pop()                 # 4001 пропал с сайта
    new = dict(site.products[-1], id=6001, name="Nothing Phone (3)", slug="nothing-phone-3")
    site.products.append(new)
    result = await sync.run()
    assert result.ok
    assert result.deactivated == 1 and result.new_items == 1
    assert (await price_of(conn, removed["id"]))[2] == 0
    since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert [p["id"] for p in await repo.new_products_since(since)] == [6001]


async def test_search_and_catalog(sync, repo):
    await sync.run()
    names = lambda rows: [r["name"] for r in rows]  # noqa: E731
    assert names(await repo.search(["iphone", "17", "pro"])) == ["iPhone 17 Pro", "iPhone 17 Pro Max"]
    # слова из описания варианта
    assert names(await repo.search(["iphone", "2", "тб"])) == ["iPhone 17 Pro Max"]
    assert names(await repo.search(["cosmic", "orange"])) == ["iPhone 17 Pro"]
    assert await repo.search(["pixel"]) == []

    top = [c["name"] for c in await repo.top_categories()]
    assert "iPhone" in top and "Misc" not in top   # пустые категории скрыты
    assert [c["name"] for c in await repo.child_categories(15)] == ["iPhone 17 Pro"]

    rows, total = await repo.category_products(15, 0, 10)
    assert total == 3
    pro = next(r for r in rows if r["id"] == 1001)
    assert pro["min_price"] == 11470000 and pro["any_stock"] == 1

    variations = await repo.get_variations(1001)
    prices = [v["price"] for v in variations]
    assert prices == sorted(prices)
