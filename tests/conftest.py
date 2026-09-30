from __future__ import annotations

import copy
import json
import os
import sys
from typing import Any

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime  # noqa: E402

from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402
from aiogram.client.session.base import BaseSession  # noqa: E402
from aiogram.methods import EditMessageReplyMarkup, EditMessageText, GetMe, SendMessage  # noqa: E402
from aiogram.types import Chat, Message, Update, User  # noqa: E402

from bot.handlers import admin, leads, user, webapp  # noqa: E402
from bot.middlewares import UserMiddleware  # noqa: E402
from config import Config  # noqa: E402
from db.database import connect  # noqa: E402
from db.repo import Repo  # noqa: E402
from services.api_client import StoreApiClient  # noqa: E402
from services.jobs import Jobs  # noqa: E402
from services.notifier import Notifier  # noqa: E402
from services.sync import SyncService  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name: str, subdir: str = "") -> list[dict[str, Any]]:
    with open(os.path.join(FIXTURES, subdir, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)["items"]


class FakeSite:
    """Имитация Store API: пагинация, заголовки X-WP-*, сбои по запросу."""

    def __init__(self, subdir: str = "") -> None:
        self.products = load_fixture("products", subdir)
        self.variations = load_fixture("variations", subdir)
        self.categories = load_fixture("categories", subdir)
        self.fail_status: int | None = None
        self.fail_on: str | None = None  # "variation" — падать только на вариантах
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        params = request.url.params
        path = request.url.path
        if path.endswith("/products/categories"):
            items = self.categories
        elif path.endswith("/products"):
            items = self.variations if params.get("type") == "variation" else self.products
        else:
            return httpx.Response(404, json={"code": "rest_no_route"})
        if self.fail_status and (self.fail_on is None or self.fail_on == params.get("type")):
            return httpx.Response(self.fail_status, text="error")
        per_page = int(params.get("per_page", 10))
        page = int(params.get("page", 1))
        chunk = items[(page - 1) * per_page: page * per_page]
        pages = max(1, -(-len(items) // per_page))
        return httpx.Response(200, json=copy.deepcopy(chunk),
                              headers={"X-WP-Total": str(len(items)), "X-WP-TotalPages": str(pages)})


@pytest.fixture
def site() -> FakeSite:
    return FakeSite()


@pytest.fixture
async def client(site: FakeSite):
    api = StoreApiClient("https://shop.test/wp-json/wc/store/v1", min_interval=0, backoff=0,
                         per_page=3, transport=httpx.MockTransport(site.handler))
    yield api
    await api.close()


@pytest.fixture
async def conn():
    c = await connect(":memory:")
    yield c
    await c.close()


@pytest.fixture
def repo(conn) -> Repo:
    return Repo(conn)


@pytest.fixture
def sync(conn, client) -> SyncService:
    return SyncService(conn, client)


# ---------- обвязка бота: апдейты через Dispatcher с подменённой сессией Telegram ----------

USER, ADMIN = 100, 200


class RecordingSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, GetMe):
            return User(id=42, is_bot=True, first_name="iPapa", username="ipapa_test_bot")
        if isinstance(method, (SendMessage, EditMessageText, EditMessageReplyMarkup)):
            return Message(message_id=1, date=datetime.now(), chat=Chat(id=1, type="private"),
                           text=getattr(method, "text", "") or "")
        return True

    async def stream_content(self, *a, **kw):  # pragma: no cover
        yield b""

    async def close(self):
        pass

    def texts(self):
        return [c.text for c in self.calls if isinstance(c, (SendMessage, EditMessageText))]


@pytest.fixture
def miniapp_url():
    return ""


@pytest.fixture
async def env(sync, repo, miniapp_url):
    await sync.run()
    config = Config(bot_token="42:TEST", admin_ids=frozenset({ADMIN}), miniapp_url=miniapp_url)
    session = RecordingSession()
    bot = Bot("42:TEST", session=session, default=DefaultBotProperties(parse_mode="HTML"))
    jobs = Jobs(config, repo, sync, Notifier(bot, repo, delay=0))
    dp = Dispatcher(repo=repo, config=config, jobs=jobs)
    dp.update.outer_middleware(UserMiddleware(repo, config.admin_ids))
    dp.include_router(admin.build_router(config.admin_ids))
    dp.include_router(leads.build_admin_router(config.admin_ids))
    dp.include_router(leads.build_router())
    dp.include_router(webapp.build_router())
    dp.include_router(user.build_router())
    counter = iter(range(1, 10_000))

    async def send_text(text, uid=USER, web_app_data=None, contact=None):
        session.calls.clear()
        msg = {"message_id": 5, "date": 0, "chat": {"id": uid, "type": "private"},
               "from": {"id": uid, "is_bot": False, "first_name": "U"}}
        if web_app_data:
            msg["web_app_data"] = {"data": web_app_data, "button_text": "Магазин"}
        elif contact:
            msg["contact"] = {"phone_number": contact, "first_name": "U", "user_id": uid}
        else:
            msg["text"] = text
            if text.startswith("/"):
                msg["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
        upd = Update.model_validate({"update_id": next(counter), "message": msg}, context={"bot": bot})
        await dp.feed_update(bot, upd)
        return session

    async def click(data, uid=USER):
        session.calls.clear()
        data = data.pack() if hasattr(data, "pack") else data
        upd = Update.model_validate({"update_id": next(counter), "callback_query": {
            "id": "1", "chat_instance": "1", "data": data,
            "from": {"id": uid, "is_bot": False, "first_name": "U"},
            "message": {"message_id": 5, "date": 0, "chat": {"id": uid, "type": "private"}, "text": "x"}}},
            context={"bot": bot})
        await dp.feed_update(bot, upd)
        return session

    yield send_text, click
    await bot.session.close()


