import json

from bot import keyboards as kb
from services.stats import full_report
from tests.conftest import ADMIN, USER


async def test_stats_report(env, repo, conn):
    send_text, click = env
    await send_text("/start")
    await click(kb.ProdCb(id=1001))                     # просмотр карточки в боте
    await send_text("iphone 17 pro")                    # поиск в боте
    await send_text("/start s5001")                     # подписка по ссылке из мини-аппа
    # мини-апп отправляет заказ и пачку своих событий
    ev = {"v": {"1002": 3, "1001": 1}, "f": [1002], "c": [5001], "k": [1001, 1002], "q": ["Айфон 17"]}
    order = {"a": "lead", "kind": "order", "items": [[5001, 1]], "phone": "+79000000000", "ev": ev}
    await send_text("", web_app_data=json.dumps(order))

    text = "\n".join(await full_report(conn, 7))
    assert "Всего: 2, активных: 2" in text or "Всего: 1, активных: 1" in text
    assert "🛒 Заказы: 1 · 1 · 1 · 1 (с телефоном: 1)" in text
    assert "1. iPhone 17 Pro Max — 3" in text          # 3 просмотра в приложении
    assert "❤️ Добавляют в избранное" in text and "📦 Заказывают" in text
    assert "iphone 17 pro — 1" in text and "айфон 17 — 1" in text
    assert "Чаще всего следят" in text

    s = await send_text("/stats 30", ADMIN)
    assert "за 30 дн." in s.texts()[0] and "Техническое" in s.texts()[-1]
