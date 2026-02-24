from __future__ import annotations

from datetime import date, datetime, time, timedelta

from bot.config import Config


def format_price(price_cents: int) -> str:
    rub = price_cents / 100
    if rub.is_integer():
        return f"{int(rub)} ₽"
    return f"{rub:.2f} ₽"


def parse_date(text: str) -> date | None:
    raw = text.strip().lower()
    today = date.today()
    if raw in {"сегодня", "today"}:
        return today
    if raw in {"завтра", "tomorrow"}:
        return today + timedelta(days=1)
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def parse_time(text: str) -> time | None:
    raw = text.strip()
    try:
        return time.fromisoformat(raw)
    except ValueError:
        return None


def combine_date_time(d: date, t: time) -> datetime:
    return datetime.combine(d, t)


def is_admin_user(config: Config, *, user_id: int | None, chat_id: int | None) -> bool:
    if user_id is not None and user_id in config.admin_user_ids:
        return True
    if config.admin_chat_id is not None and chat_id == config.admin_chat_id:
        return True
    return False
