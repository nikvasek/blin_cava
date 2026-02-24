from __future__ import annotations

import json
from typing import Any

from aiogram import F, Router
from aiogram.types import Message

from bot.config import Config
from bot.db import create_order, fetch_menu_item_by_category_title
from bot.keyboards import open_webapp_kb
from bot.utils import format_price


router = Router(name=__name__)


def _clean_text(v: Any, *, max_len: int) -> str:
    s = str(v or "").strip()
    if len(s) > max_len:
        s = s[:max_len]
    return s


@router.message(F.web_app_data)
async def webapp_checkout(message: Message, config: Config) -> None:
    raw = getattr(message.web_app_data, "data", None)
    if not raw:
        await message.answer("Не получил данные из мини‑приложения.")
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        await message.answer("Данные из мини‑приложения повреждены.")
        return

    if not isinstance(payload, dict):
        await message.answer("Неверный формат данных из мини‑приложения.")
        return

    name = _clean_text(payload.get("name"), max_len=64)
    phone = _clean_text(payload.get("phone"), max_len=32)
    address = _clean_text(payload.get("address"), max_len=256)
    comment = _clean_text(payload.get("comment"), max_len=512)

    if len(name) < 2:
        await message.answer("Не понял имя. Вернитесь в мини‑приложение и заполните поле имени.")
        return
    if len(phone) < 6:
        await message.answer("Не понял телефон. Вернитесь в мини‑приложение и заполните телефон.")
        return
    if len(address) < 6:
        await message.answer("Не понял адрес. Вернитесь в мини‑приложение и заполните адрес доставки.")
        return

    items_raw = payload.get("items")
    if not isinstance(items_raw, list) or not items_raw:
        await message.answer("Корзина пуста.")
        return

    items: list[dict[str, Any]] = []
    human_lines: list[str] = []
    total_cents = 0

    for it in items_raw:
        if not isinstance(it, dict):
            continue

        category = _clean_text(it.get("category"), max_len=64)
        title = _clean_text(it.get("title"), max_len=128)
        try:
            qty = int(it.get("qty", 0))
        except (TypeError, ValueError):
            qty = 0

        if not category or not title or qty <= 0 or qty > 100:
            continue

        menu_item = await fetch_menu_item_by_category_title(
            config.db_path,
            category=category,
            title=title,
        )
        if not menu_item:
            continue

        items.append(
            {
                "menu_item_id": int(menu_item.id),
                "qty": int(qty),
                "price_cents": int(menu_item.price_cents),
            }
        )

        line_total = int(menu_item.price_cents) * int(qty)
        total_cents += line_total
        human_lines.append(f"• {menu_item.title} ×{qty} = {format_price(line_total)}")

    if not items:
        await message.answer(
            "Не смог сопоставить выбранные позиции с текущим меню. "
            "Попробуйте обновить мини‑приложение и собрать заказ заново.",
            reply_markup=open_webapp_kb(config.webapp_url) if config.webapp_url else None,
        )
        return

    order_id = await create_order(
        config.db_path,
        user_id=message.from_user.id if message.from_user else 0,
        order_type="delivery",
        scheduled_for=None,
        name=name,
        phone=phone,
        address=address,
        comment=comment,
        items=items,
    )

    text = (
        f"✅ Заказ оформлен. Номер: {order_id}\n\n"
        f"Доставка: {address}\n"
        f"Имя: {name}\n"
        f"Тел: {phone}\n\n"
        + "\n".join(human_lines)
        + f"\n\nИтого: {format_price(total_cents)}"
    )

    await message.answer(text)

    if config.admin_chat_id:
        admin_text = (
            f"🆕 Новый заказ #{order_id}\n"
            f"Тип: delivery\n"
            f"Имя: {name}\n"
            f"Тел: {phone}\n"
            f"Адрес: {address}\n\n"
            + "\n".join(human_lines)
            + f"\n\nИтого: {format_price(total_cents)}\n"
            + (f"Комментарий: {comment}\n" if comment else "")
        )
        try:
            await message.bot.send_message(config.admin_chat_id, admin_text)
        except Exception:
            pass
