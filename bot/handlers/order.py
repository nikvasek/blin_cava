from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from typing import Any, Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.db import create_order, fetch_categories, fetch_menu_item, fetch_menu_items
from bot.db import fetch_menu_item_by_category_title
from bot.keyboards import (
    categories_kb,
    contact_kb,
    main_menu_kb,
    order_type_kb,
    yes_no_kb,
)
from bot.utils import format_price, is_admin_user, parse_date, parse_time


router = Router(name=__name__)


async def _start_checkout_from_cart(message: Message, state: FSMContext, config: Config) -> None:
    await state.set_state(OrderFlow.choosing_type)
    include_admin = is_admin_user(
        config,
        user_id=message.from_user.id if message.from_user else None,
        chat_id=message.chat.id,
    )
    await message.answer(
        "Корзина получена. Выберите тип заказа:",
        reply_markup=main_menu_kb(include_admin=include_admin),
    )
    await message.answer("Тип заказа:", reply_markup=order_type_kb())


@router.message(F.web_app_data)
async def webapp_cart(message: Message, state: FSMContext, config: Config) -> None:
    """Receive cart from Telegram Mini App via WebApp.sendData()."""

    raw = getattr(message.web_app_data, "data", None)
    if not raw:
        await message.answer("Не получил данные из мини‑приложения.")
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        await message.answer("Данные из мини‑приложения повреждены.")
        return

    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        await message.answer("Корзина пуста.")
        return

    name = str(payload.get("name", "")).strip() if isinstance(payload, dict) else ""
    phone = str(payload.get("phone", "")).strip() if isinstance(payload, dict) else ""
    address = str(payload.get("address", "")).strip() if isinstance(payload, dict) else ""
    comment = str(payload.get("comment", "")).strip() if isinstance(payload, dict) else ""

    cart: dict[str, int] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        category = str(it.get("category", "")).strip()
        title = str(it.get("title", "")).strip()
        qty_raw = it.get("qty", 0)
        try:
            qty = int(qty_raw)
        except (TypeError, ValueError):
            qty = 0

        if not category or not title or qty <= 0:
            continue

        menu_item = await fetch_menu_item_by_category_title(
            config.db_path,
            category=category,
            title=title,
        )
        if not menu_item:
            continue
        cart[str(menu_item.id)] = cart.get(str(menu_item.id), 0) + qty

    if not cart:
        await message.answer(
            "Не смог сопоставить выбранные позиции с текущим меню."
        )
        return

    # If the mini app provided delivery form fields, finalize order immediately.
    if name and phone and address:
        db_items: list[dict[str, Any]] = []
        for item_id_str, qty in cart.items():
            mi = await fetch_menu_item(config.db_path, int(item_id_str))
            if not mi:
                continue
            db_items.append(
                {
                    "menu_item_id": int(mi.id),
                    "qty": int(qty),
                    "price_cents": int(mi.price_cents),
                }
            )

        if not db_items:
            await message.answer("Корзина пуста.")
            return

        await state.clear()

        order_id = await create_order(
            config.db_path,
            user_id=message.from_user.id,
            order_type="delivery",
            scheduled_for=None,
            name=name,
            phone=phone,
            address=address,
            comment=comment,
            items=db_items,
        )

        include_admin = is_admin_user(
            config,
            user_id=message.from_user.id if message.from_user else None,
            chat_id=message.chat.id,
        )
        await message.answer(
            f"✅ Заказ оформлен. Номер: {order_id}",
            reply_markup=main_menu_kb(include_admin=include_admin),
        )

        if config.admin_chat_id:
            cart_text, _ = await _render_cart(config, cart)
            text = (
                f"🆕 Новый заказ #{order_id}\n"
                f"Тип: delivery\n"
                f"Имя: {name}\n"
                f"Тел: {phone}\n"
                f"Адрес: {address}\n\n"
                f"{cart_text}\n\n"
                f"Комментарий: {comment or '-'}"
            )
            try:
                await message.bot.send_message(config.admin_chat_id, text)
            except Exception:
                pass

        return

    # Fallback to the old chat-based checkout flow.
    await state.clear()
    await state.update_data(cart=cart)

    cart_text, total = await _render_cart(config, cart)
    await message.answer(cart_text)
    if total <= 0:
        return

    await _start_checkout_from_cart(message, state, config)


class OrderFlow(StatesGroup):
    choosing_type = State()
    choosing_when = State()
    scheduling_date = State()
    scheduling_time = State()
    contact_name = State()
    contact_phone = State()
    delivery_address = State()
    confirm = State()


def _cart_key(user_id: int) -> str:
    return f"cart:{user_id}"


async def _get_cart(state: FSMContext) -> dict[str, Any]:
    data = await state.get_data()
    return dict(data.get("cart", {}))


async def _set_cart(state: FSMContext, cart: dict[str, Any]) -> None:
    await state.update_data(cart=cart)


async def _render_cart(config: Config, cart: dict[str, Any]) -> tuple[str, int]:
    if not cart:
        return "Корзина пуста.", 0
    lines: list[str] = ["🧺 Корзина:\n"]
    total = 0
    for item_id_str, qty in cart.items():
        item_id = int(item_id_str)
        item = await fetch_menu_item(config.db_path, item_id)
        if not item:
            continue
        line_total = item.price_cents * int(qty)
        total += line_total
        lines.append(
            f"• {item.title} × {qty} = {format_price(line_total)}"
        )
    lines.append(f"\nИтого: {format_price(total)}")
    return "\n".join(lines), total


@router.message(F.text == "🛍 Заказ: доставка/самовывоз")
async def start_order(message: Message, state: FSMContext, config: Config) -> None:
    await state.clear()
    await state.set_state(OrderFlow.choosing_type)
    include_admin = is_admin_user(
        config,
        user_id=message.from_user.id if message.from_user else None,
        chat_id=message.chat.id,
    )
    await message.answer(
        "Выберите тип заказа:",
        reply_markup=main_menu_kb(include_admin=include_admin),
    )
    await message.answer("Тип заказа:", reply_markup=order_type_kb())


@router.callback_query(F.data.startswith("order:type:"))
async def set_order_type(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    order_type = call.data.split(":")[-1]
    await state.update_data(order_type=order_type, cart={})
    await state.set_state(None)
    categories = await fetch_categories(config.db_path)
    await call.message.answer("Ок. Теперь выберите блюда:")
    await call.message.answer(
        "Категории для заказа:",
        reply_markup=categories_kb(categories, for_order=True),
    )
    await call.answer()


@router.callback_query(F.data.startswith("order_cat:"))
async def order_category(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    category = call.data.split(":", 1)[1]
    items = await fetch_menu_items(config.db_path, category)
    if not items:
        await call.answer("Пусто")
        return
    lines = [f"{category}:\n"]
    for it in items:
        lines.append(f"• {it.title} — {format_price(it.price_cents)}")
    lines.append("\nНажимайте ➕/➖, затем откройте корзину.")

    from bot.keyboards import order_items_kb

    cart = await _get_cart(state)
    await state.update_data(order_last_category=category)
    await call.message.answer(
        "\n".join(lines),
        reply_markup=order_items_kb([(it.id, it.title) for it in items], cart=cart),
    )
    await call.answer()


@router.callback_query(F.data.startswith("cart:inc:"))
async def cart_inc(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    item_id = call.data.split(":")[-1]
    cart = await _get_cart(state)
    cart[item_id] = int(cart.get(item_id, 0)) + 1
    await _set_cart(state, cart)

    last_category = (await state.get_data()).get("order_last_category")
    if last_category and call.message:
        from bot.keyboards import order_items_kb

        items = await fetch_menu_items(config.db_path, str(last_category))
        await call.message.edit_reply_markup(
            reply_markup=order_items_kb([(it.id, it.title) for it in items], cart=cart)
        )
    await call.answer("Добавлено")


@router.callback_query(F.data.startswith("cart:dec:"))
async def cart_dec(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    item_id = call.data.split(":")[-1]
    cart = await _get_cart(state)
    current = int(cart.get(item_id, 0))
    if current <= 1:
        cart.pop(item_id, None)
    else:
        cart[item_id] = current - 1
    await _set_cart(state, cart)

    last_category = (await state.get_data()).get("order_last_category")
    if last_category and call.message:
        from bot.keyboards import order_items_kb

        items = await fetch_menu_items(config.db_path, str(last_category))
        await call.message.edit_reply_markup(
            reply_markup=order_items_kb([(it.id, it.title) for it in items], cart=cart)
        )
    await call.answer("Ок")


@router.callback_query(F.data == "cart:view")
async def cart_view(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    cart = await _get_cart(state)
    text, total = await _render_cart(config, cart)
    if total <= 0:
        await call.message.answer(text)
        await call.answer()
        return

    await call.message.answer(text)
    await call.message.answer(
        "Оформляем?",
        reply_markup=yes_no_kb("order:checkout", "order:keep"),
    )
    await call.answer()


@router.callback_query(F.data == "order:keep")
async def order_keep(call: CallbackQuery) -> None:
    await call.answer("Ок")


@router.callback_query(F.data == "order:checkout")
async def order_checkout(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OrderFlow.choosing_when)
    await call.message.answer(
        "Когда приготовить/доставить? Напишите `сейчас` или дату (YYYY-MM-DD).",
    )
    await call.answer()


@router.message(OrderFlow.choosing_when)
async def order_when(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().lower()
    if raw in {"сейчас", "как можно скорее", "now"}:
        await state.update_data(scheduled_for=None)
        await state.set_state(OrderFlow.contact_name)
        await message.answer("Как к вам обращаться?")
        return

    d = parse_date(raw)
    if not d:
        await message.answer("Не понял дату. Пример: 2026-02-23 или 'сегодня'.")
        return
    await state.update_data(schedule_date=d.isoformat())
    await state.set_state(OrderFlow.scheduling_time)
    await message.answer("Ок. Введите время (HH:MM), например 19:30")


@router.message(OrderFlow.scheduling_time)
async def order_time(message: Message, state: FSMContext) -> None:
    t = parse_time(message.text or "")
    if not t:
        await message.answer("Не понял время. Пример: 19:30")
        return
    data = await state.get_data()
    d = parse_date(data.get("schedule_date", ""))
    if not d:
        await state.set_state(OrderFlow.choosing_when)
        await message.answer("Давайте заново: напишите дату.")
        return
    scheduled_for = datetime.combine(d, t)
    await state.update_data(scheduled_for=scheduled_for.isoformat(sep=" "))
    await state.set_state(OrderFlow.contact_name)
    await message.answer("Как к вам обращаться?")


@router.message(OrderFlow.contact_name)
async def order_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Напишите имя чуть подробнее.")
        return
    await state.update_data(name=name)
    await state.set_state(OrderFlow.contact_phone)
    await message.answer("Отправьте номер телефона:", reply_markup=contact_kb())


@router.message(OrderFlow.contact_phone, F.contact)
async def order_phone_contact(message: Message, state: FSMContext) -> None:
    await state.update_data(phone=message.contact.phone_number)
    await _next_after_phone(message, state)


@router.message(OrderFlow.contact_phone)
async def order_phone_text(message: Message, state: FSMContext) -> None:
    phone = (message.text or "").strip()
    if len(phone) < 6:
        await message.answer("Похоже на некорректный номер. Попробуйте ещё раз.")
        return
    await state.update_data(phone=phone)
    await _next_after_phone(message, state)


async def _next_after_phone(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("order_type") == "delivery":
        await state.set_state(OrderFlow.delivery_address)
        await message.answer("Введите адрес доставки (улица, дом, квартира):")
        return
    await state.set_state(OrderFlow.confirm)
    await message.answer("Есть комментарий к заказу? Если нет — напишите '-' ")


@router.message(OrderFlow.delivery_address)
async def order_address(message: Message, state: FSMContext) -> None:
    addr = (message.text or "").strip()
    if len(addr) < 6:
        await message.answer("Адрес слишком короткий. Попробуйте ещё раз.")
        return
    await state.update_data(address=addr)
    await state.set_state(OrderFlow.confirm)
    await message.answer("Есть комментарий к заказу? Если нет — напишите '-' ")


@router.message(OrderFlow.confirm)
async def order_confirm(message: Message, state: FSMContext, config: Config) -> None:
    comment = (message.text or "").strip()
    if comment == "-":
        comment = ""

    data = await state.get_data()
    cart = dict(data.get("cart", {}))
    if not cart:
        include_admin = is_admin_user(
            config,
            user_id=message.from_user.id if message.from_user else None,
            chat_id=message.chat.id,
        )
        await message.answer("Корзина пуста.", reply_markup=main_menu_kb(include_admin=include_admin))
        await state.clear()
        return

    items: list[dict[str, Any]] = []
    for item_id_str, qty in cart.items():
        item = await fetch_menu_item(config.db_path, int(item_id_str))
        if not item:
            continue
        items.append(
            {
                "menu_item_id": item.id,
                "qty": int(qty),
                "price_cents": item.price_cents,
            }
        )

    scheduled_for_iso = data.get("scheduled_for")
    scheduled_for: Optional[datetime] = (
        datetime.fromisoformat(scheduled_for_iso) if scheduled_for_iso else None
    )

    order_id = await create_order(
        config.db_path,
        user_id=message.from_user.id,
        order_type=str(data.get("order_type", "pickup")),
        scheduled_for=scheduled_for,
        name=str(data.get("name", "")),
        phone=str(data.get("phone", "")),
        address=data.get("address"),
        comment=comment,
        items=items,
    )

    await message.answer(
        f"✅ Заказ оформлен. Номер: {order_id}",
        reply_markup=main_menu_kb(
            include_admin=is_admin_user(
                config,
                user_id=message.from_user.id if message.from_user else None,
                chat_id=message.chat.id,
            )
        ),
    )

    if config.admin_chat_id:
        cart_text, _ = await _render_cart(config, cart)
        text = (
            f"🆕 Новый заказ #{order_id}\n"
            f"Тип: {data.get('order_type')}\n"
            f"Имя: {data.get('name')}\n"
            f"Тел: {data.get('phone')}\n"
            f"Адрес: {data.get('address', '-') }\n\n"
            f"{cart_text}\n\n"
            f"Комментарий: {comment or '-'}"
        )
        try:
            await message.bot.send_message(config.admin_chat_id, text)
        except Exception:
            pass

    await state.clear()
