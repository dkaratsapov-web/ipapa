"""Отчёты для администраторов: /changes и ежедневная сводка."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
from zoneinfo import ZoneInfo

from bot.formatting import change_line, fmt_dt, item_title, split_messages
from db.repo import Repo
from services.parsing import format_price


def _since(hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="microseconds")


async def changes_report(repo: Repo, hours: float, tz: ZoneInfo) -> list[str]:
    events = await repo.price_changes_since(_since(hours))
    if not events:
        return [f"За последние {hours:g} ч изменений цен нет."]
    header = f"📈 <b>Изменения цен за {hours:g} ч: {len(events)}</b>"
    lines = [f"{fmt_dt(ev['changed_at'], tz)[:5]}{fmt_dt(ev['changed_at'], tz)[-6:]} {change_line(ev)}" for ev in events]
    return split_messages(lines, header)


async def daily_digest(repo: Repo, tz: ZoneInfo) -> list[str]:
    since = _since(24)
    changes = await repo.price_changes_since(since)
    gone = await repo.out_of_stock_since(since)
    new = await repo.new_products_since(since)

    ups = sum(1 for ev in changes if ev["new_price"] > ev["old_price"])
    lines = [
        f"🗞 <b>Сводка за 24 ч</b> ({datetime.now(tz).strftime('%d.%m.%Y')})",
        f"Изменений цен: {len(changes)} (↑ {ups}, ↓ {len(changes) - ups})",
        f"Новых товаров: {len(new)}",
        f"Пропали из наличия: {len(gone)}",
    ]
    top = sorted(changes, key=lambda ev: abs(ev["new_price"] - ev["old_price"]), reverse=True)[:10]
    if top:
        lines += ["", "<b>Топ-10 изменений:</b>"]
        lines += [f"{i}. {change_line(ev)}" for i, ev in enumerate(top, 1)]
    if new:
        lines += ["", "<b>Новые товары:</b>"]
        lines += [f"• <a href=\"{escape(p['permalink'])}\">{escape(p['name'])}</a> — "
                  f"{format_price(p['min_price'])}" for p in new[:30]]
        if len(new) > 30:
            lines.append(f"… и ещё {len(new) - 30}")
    if gone:
        lines += ["", "<b>Пропали из наличия:</b>"]
        lines += [f"• {escape(item_title(ev))}" for ev in gone[:30]]
        if len(gone) > 30:
            lines.append(f"… и ещё {len(gone) - 30}")
    from services.stats import digest_lines
    lines += await digest_lines(repo.conn)
    return split_messages(lines)
