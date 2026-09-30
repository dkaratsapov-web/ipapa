"""Загрузка конфигурации из .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

DEFAULT_API_URL = "https://xn--80aaa8a4ab.xn--p1ai/wp-json/wc/store/v1"


def _parse_ids(raw: str) -> frozenset[int]:
    return frozenset(int(x) for x in raw.replace(" ", "").split(",") if x)


def _parse_time(raw: str) -> time:
    hh, mm = raw.strip().split(":")
    return time(int(hh), int(mm))


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: frozenset[int] = field(default_factory=frozenset)
    sync_interval_min: int = 60
    digest_time: time = time(10, 0)
    tz_name: str = "Europe/Moscow"
    db_path: str = "data/ipapa.db"
    log_path: str = "data/bot.log"
    site_api_url: str = DEFAULT_API_URL
    run_duration_min: int = 0  # 0 — работать бессрочно; >0 — остановиться через N минут
    miniapp_url: str = ""      # адрес мини-аппа (https), пусто — кнопка не показывается
    export_path: str = ""      # куда писать catalog.json для мини-аппа
    export_cmd: str = ""       # команда публикации выгрузки после синхронизации
    leads_chat_id: int = 0     # чат менеджеров для заявок; 0 — отправлять администраторам

    @property
    def site_url(self) -> str:
        return self.site_api_url.split("/wp-json")[0]

    @property
    def lead_recipients(self) -> list[int]:
        return [self.leads_chat_id] if self.leads_chat_id else sorted(self.admin_ids)

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.tz_name)


def load_config() -> Config:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN не задан (см. .env.example)")
    return Config(
        bot_token=token,
        admin_ids=_parse_ids(os.getenv("ADMIN_IDS", "")),
        sync_interval_min=int(os.getenv("SYNC_INTERVAL_MIN", "60")),
        digest_time=_parse_time(os.getenv("DIGEST_TIME", "10:00")),
        tz_name=os.getenv("TZ", "Europe/Moscow"),
        db_path=os.getenv("DB_PATH", "data/ipapa.db"),
        log_path=os.getenv("LOG_PATH", "data/bot.log"),
        site_api_url=os.getenv("SITE_API_URL", DEFAULT_API_URL).rstrip("/"),
        run_duration_min=int(os.getenv("RUN_DURATION_MIN", "0") or 0),
        miniapp_url=os.getenv("MINIAPP_URL", "").strip(),
        export_path=os.getenv("EXPORT_PATH", "").strip(),
        export_cmd=os.getenv("EXPORT_CMD", "").strip(),
        leads_chat_id=int(os.getenv("LEADS_CHAT_ID", "0") or 0),
    )
