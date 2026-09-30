"""Прогон апдейтов через Dispatcher с подменённой сессией Telegram (обвязка — в conftest)."""
import pytest
from aiogram.methods import EditMessageText, SendMessage, SetChatMenuButton

from bot import keyboards as kb
from tests.conftest import ADMIN, USER


async def test_user_flow(env, repo):
    send_text, click = env
    s = await send_text("/start")
    assert "айпапа.рф" in s.texts()[0]

    s = await click(kb.MenuCb(action="catalog"))
    assert "Каталог" in s.texts()[0]

    s = await click(kb.CatCb(id=15, page=-1))            # есть подкатегории
    assert "iPhone" in s.texts()[0]
    s = await click(kb.CatCb(id=15, page=0))             # список товаров
    assert "товаров: 3" in s.texts()[0]

    s = await click(kb.ProdCb(id=1001, cat=15, page=0))  # карточка
    card = s.texts()[0]
    assert "iPhone 17 Pro" in card and "✅ 256 ГБ · Silver · eSIM — <b>114 700 ₽</b>" in card
    assert "<s>159 900 ₽</s>" in card                    # скидка зачёркнута
    assert "Обновлено:" in card
    edit = next(c for c in s.calls if isinstance(c, EditMessageText))
    assert edit.link_preview_options.url.endswith("iphone-17-pro.jpg")

    s = await click(kb.SubMenuCb(pid=1001))
    s = await click(kb.SubAddCb(id=5001, pid=1001))
    assert await repo.subscribed_ids(USER) == {5001}
    s = await click(kb.MenuCb(action="subs"))
    assert "Мои подписки" in s.texts()[0]
    subs = await repo.user_subscriptions(USER)
    await click(kb.UnsubCb(sub_id=subs[0]["sub_id"]))
    assert await repo.subscribed_ids(USER) == set()

    s = await send_text("iphone 17 pro")
    assert "Найдено: 2" in s.texts()[0]
    s = await send_text("несуществующий товар")
    assert "Ничего не нашлось" in s.texts()[0]


async def test_admin_commands(env, conn):
    send_text, _ = env
    await send_text("/start", USER)
    s = await send_text("/stats", ADMIN)
    assert "Подписок: 0" in s.texts()[0]
    assert "Пользователей: 2 (активных 2)" in s.texts()[0]

    await conn.execute("UPDATE products SET price = 11970000 WHERE id = 5001")
    await conn.commit()
    s = await send_text("/sync", ADMIN)
    assert "Изменений цен: 1" in s.texts()[-1]
    s = await send_text("/changes 2", ADMIN)
    assert "−5 000 ₽" in s.texts()[0]
    s = await send_text("/changes abc", ADMIN)
    assert "Использование" in s.texts()[0]
    s = await send_text("/digest", ADMIN)
    assert "Сводка за 24 ч" in s.texts()[0]

    # не-админ: команда не выполняется и не уходит в поиск
    s = await send_text("/sync", USER)
    assert s.texts() == []


@pytest.mark.parametrize("miniapp_url", ["https://example.github.io/ipapa/"])
async def test_miniapp_integration(env, repo):
    send_text, click = env
    s = await send_text("/start")
    kb_msg = [c for c in s.calls if isinstance(c, SendMessage)][-1]
    url = kb_msg.reply_markup.keyboard[0][0].web_app.url
    assert url.startswith("https://example.github.io/ipapa/?bot=ipapa_test_bot") and "m=kb" in url
    assert any(isinstance(c, SetChatMenuButton) for c in s.calls)

    # подписка из мини-аппа через sendData
    s = await send_text("", web_app_data='{"a":"sub","id":5001}')
    assert await repo.subscribed_ids(USER) == {5001}
    reply = [c for c in s.calls if isinstance(c, SendMessage)][-1]
    assert "Слежу за ценой" in reply.text and "subs=5001" in reply.reply_markup.keyboard[0][0].web_app.url

    # подписка и отписка через deep link
    await send_text("/start s1002")
    assert await repo.subscribed_ids(USER) == {5001, 1002}
    await send_text("/start u5001")
    assert await repo.subscribed_ids(USER) == {1002}

    # пакет из мини-аппа: две подписки и одна отписка
    s = await send_text("", web_app_data='{"a":"batch","sub":[5002,1001],"unsub":[1002]}')
    assert await repo.subscribed_ids(USER) == {5002, 1001}
    text = [c for c in s.calls if isinstance(c, SendMessage)][-1].text
    assert "Слежу за ценой" in text and "Больше не слежу" in text
    await send_text("/start u5002_1001-s5001_5003")
    assert await repo.subscribed_ids(USER) == {5001, 5003}

    # ссылка на товар открывает карточку
    s = await send_text("/start p1001")
    assert "iPhone 17 Pro" in s.texts()[-1]

    # мусор из мини-аппа игнорируется
    s = await send_text("", web_app_data="not json")
    assert s.texts() == []

    # кнопка «Открыть в приложении» в карточке товара
    s = await click(kb.ProdCb(id=1001))
    edit = next(c for c in s.calls if isinstance(c, EditMessageText))
    assert "p=1001" in edit.reply_markup.inline_keyboard[0][0].web_app.url
