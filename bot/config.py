from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_chat_id: Optional[int]
    admin_user_ids: frozenset[int]
    db_path: str
    hall_plan_path: str
    webapp_url: Optional[str]


def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Put it into .env")

    admin_chat_id_raw = os.getenv("ADMIN_CHAT_ID", "").strip()
    admin_chat_id = int(admin_chat_id_raw) if admin_chat_id_raw else None

    admin_user_ids_raw = os.getenv("ADMIN_USER_IDS", "").strip()
    admin_user_ids: set[int] = set()
    if admin_user_ids_raw:
        for part in admin_user_ids_raw.replace(";", ",").split(","):
            p = part.strip()
            if not p:
                continue
            admin_user_ids.add(int(p))

    db_path = os.getenv("DB_PATH", "data/cafe.db").strip()
    hall_plan_path = os.getenv("HALL_PLAN_PATH", "assets/hall_plan.png").strip()
    webapp_url = os.getenv("WEBAPP_URL", "").strip() or None
    if webapp_url and not webapp_url.startswith("https://"):
        raise RuntimeError(
            "WEBAPP_URL must start with https:// (Telegram WebApps require HTTPS). "
            "For local dev, use a tunnel like ngrok/Cloudflare Tunnel."
        )

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return Config(
        bot_token=bot_token,
        admin_chat_id=admin_chat_id,
        admin_user_ids=frozenset(admin_user_ids),
        db_path=db_path,
        hall_plan_path=hall_plan_path,
        webapp_url=webapp_url,
    )
