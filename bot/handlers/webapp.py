from __future__ import annotations

import json
from typing import Any

from aiogram import F, Router
from aiogram.types import Message

from bot.config import Config
from bot.db import create_order, fetch_menu_item_by_category_title, upsert_menu_item
from bot.keyboards import open_webapp_kb
from bot.utils import format_price


router = Router(name=__name__)


def _clean_text(v: Any, *, max_len: int) -> str:
    s = str(v or "").strip()
    if len(s) > max_len:
        s = s[:max_len]
    return s


def _admin_targets(config: Config) -> set[int]:
    targets: set[int] = set()
    if config.admin_chat_id is not None:
        targets.add(int(config.admin_chat_id))
    targets.update(int(x) for x in config.admin_user_ids)
    return targets


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

    order_type = _clean_text(payload.get("order_type"), max_len=16) or "delivery"
    if order_type not in {"delivery", "pickup"}:
        order_type = "delivery"

    name = _clean_text(payload.get("name"), max_len=64)
    phone = _clean_text(payload.get("phone"), max_len=32)
    address = _clean_text(payload.get("address"), max_len=256)
    pickup_time = _clean_text(payload.get("pickup_time"), max_len=32)
    delivery_time = _clean_text(payload.get("delivery_time"), max_len=32)
    comment = _clean_text(payload.get("comment"), max_len=512)

    if len(name) < 2:
        await message.answer("Не понял имя. Вернитесь в мини‑приложение и заполните поле имени.")
        return
    if len(phone) < 6:
        await message.answer("Не понял телефон. Вернитесь в мини‑приложение и заполните телефон.")
        return
    if order_type == "delivery" and len(address) < 6:
        await message.answer("Не понял адрес. Вернитесь в мини‑приложение и заполните адрес доставки.")
        return
    if order_type == "delivery" and len(delivery_time) < 2:
        await message.answer("Не понял время доставки. Вернитесь в мини‑приложение и заполните время.")
        return
    if order_type == "pickup" and len(pickup_time) < 2:
        await message.answer("Не понял время самовывоза. Вернитесь в мини‑приложение и заполните время.")
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
        description = _clean_text(it.get("description"), max_len=512)
        try:
            qty = int(it.get("qty", 0))
        except (TypeError, ValueError):
            qty = 0
        price_raw = it.get("price")
        try:
            price_rub = float(price_raw)
        except (TypeError, ValueError):
            price_rub = 0.0

        price_cents = int(round(price_rub * 100))

        if not category or not title or qty <= 0 or qty > 100 or price_cents <= 0:
            continue

        menu_item = await fetch_menu_item_by_category_title(
            config.db_path,
            category=category,
            title=title,
        )
        if not menu_item or int(menu_item.price_cents) != int(price_cents):
            menu_item = await upsert_menu_item(
                config.db_path,
                category=category,
                title=title,
                description=description,
                price_cents=price_cents,
            )

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
        order_type=order_type,
        scheduled_for=None,
        name=name,
        phone=phone,
        address=address if order_type == "delivery" else None,
        comment=comment,
        items=items,
    )

    text = (
        f"✅ Заказ оформлен. Номер: {order_id}\n\n"
        f"Тип: {order_type}\n"
        + (f"Доставка: {address}\n" if order_type == "delivery" else "")
        + (f"Время доставки: {delivery_time}\n" if order_type == "delivery" else "")
        + (f"Самовывоз: {pickup_time}\n" if order_type == "pickup" else "")
        + f"Имя: {name}\n"
        + f"Тел: {phone}\n\n"
        + "\n".join(human_lines)
        + f"\n\nИтого: {format_price(total_cents)}"
    )

    await message.answer(
        text,
        reply_markup=open_webapp_kb(config.webapp_url) if config.webapp_url else None,
    )

    admin_targets = _admin_targets(config)
    if admin_targets:
        admin_text = (
            f"🆕 Новый заказ #{order_id}\n"
            f"Тип: {order_type}\n"
            f"Имя: {name}\n"
            f"Тел: {phone}\n"
            + (f"Адрес: {address}\n" if order_type == "delivery" else "")
            + (f"Время доставки: {delivery_time}\n" if order_type == "delivery" else "")
            + (f"Время самовывоза: {pickup_time}\n" if order_type == "pickup" else "")
            + "\n"
            + "\n".join(human_lines)
            + f"\n\nИтого: {format_price(total_cents)}\n"
            + (f"Комментарий: {comment}\n" if comment else "")
        )
        for chat_id in admin_targets:
            try:
                await message.bot.send_message(chat_id, admin_text)
            except Exception:
                continue
