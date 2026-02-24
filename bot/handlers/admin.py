from __future__ import annotations

import re
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.db import (
    fetch_active_menu_items,
    fetch_menu_item,
    fetch_order_items,
    fetch_recent_orders,
    fetch_recent_reservations,
    update_menu_item_price,
    update_order_status,
    update_reservation_status,
)
from bot.keyboards import (
    admin_booking_actions_kb,
    admin_bookings_kb,
    admin_item_actions_kb,
    admin_items_kb,
    admin_order_actions_kb,
    admin_orders_kb,
    main_menu_kb,
)
from bot.utils import format_price, is_admin_user


router = Router(name=__name__)


class AdminFlow(StatesGroup):
    waiting_price = State()


def _parse_price_to_cents(text: str) -> Optional[int]:
    raw = (text or "").strip().lower()
    raw = raw.replace("₽", "").replace("р", "").replace("руб", "")
    raw = raw.replace(" ", "")
    if not raw:
        return None

    # Accept: 930 / 930.50 / 930,50
    raw = raw.replace(",", ".")
    if not re.fullmatch(r"\d+(\.\d{1,2})?", raw):
        return None

    try:
        val = float(raw)
    except ValueError:
        return None

    if val <= 0 or val > 1_000_000:
        return None

    return int(round(val * 100))


async def _admin_send_items(message: Message, config: Config) -> None:
    items = await fetch_active_menu_items(config.db_path)
    if not items:
        await message.answer("Активных позиций нет.")
        return

    buttons: list[tuple[int, str]] = []
    for it in items:
        buttons.append((it.id, f"{it.category}: {it.title} — {format_price(it.price_cents)}"))

    await message.answer("Выберите позицию для редактирования:", reply_markup=admin_items_kb(buttons))


async def _admin_send_orders(message: Message, config: Config) -> None:
    orders = await fetch_recent_orders(config.db_path, limit=20)
    if not orders:
        await message.answer("Заказов пока нет.")
        return

    buttons: list[tuple[int, str]] = []
    for o in orders:
        when = o.scheduled_for or "сейчас"
        buttons.append(
            (o.id, f"#{o.id} {o.type}/{o.status} — {format_price(o.total_cents)} ({when})")
        )

    await message.answer("Последние заказы:", reply_markup=admin_orders_kb(buttons))


async def _admin_send_bookings(message: Message, config: Config) -> None:
    res = await fetch_recent_reservations(config.db_path, limit=20)
    if not res:
        await message.answer("Броней пока нет.")
        return

    buttons: list[tuple[int, str]] = []
    for r in res:
        buttons.append((r.id, f"#{r.id} {r.table_code} {r.start_at} ({r.guests}) {r.status}"))

    await message.answer("Последние брони:", reply_markup=admin_bookings_kb(buttons))


@router.message(Command("admin"))
async def admin_root(message: Message, state: FSMContext, config: Config) -> None:
    if not is_admin_user(config, user_id=message.from_user.id if message.from_user else None, chat_id=message.chat.id):
        await message.answer("Нет доступа.")
        return

    await state.clear()
    await _admin_send_items(message, config)


@router.message(Command("orders"))
async def admin_orders_cmd(message: Message, state: FSMContext, config: Config) -> None:
    if not is_admin_user(config, user_id=message.from_user.id if message.from_user else None, chat_id=message.chat.id):
        await message.answer("Нет доступа.")
        return
    await state.clear()
    await _admin_send_orders(message, config)


@router.message(Command("bookings"))
async def admin_bookings_cmd(message: Message, state: FSMContext, config: Config) -> None:
    if not is_admin_user(config, user_id=message.from_user.id if message.from_user else None, chat_id=message.chat.id):
        await message.answer("Нет доступа.")
        return
    await state.clear()
    await _admin_send_bookings(message, config)


@router.message(Command("admin_help"))
@router.message(F.text == "🛠 Админ команды")
async def admin_help(message: Message, config: Config) -> None:
    if not is_admin_user(config, user_id=message.from_user.id if message.from_user else None, chat_id=message.chat.id):
        await message.answer("Нет доступа.")
        return

    lines = [
        "📌 Команды бота (с пояснениями)",
        "",
        "Пользовательские:",
        "• /start — показать главное меню",
        "• /cancel — отменить текущий ввод/сценарий",
        "• /app — открыть мини‑приложение (если настроен WEBAPP_URL)",
        "",
        "Кнопки в меню:",
        "• 🍽 Меню — посмотреть категории и позиции",
        "• 🛍 Заказ: доставка/самовывоз — собрать корзину и оформить заказ",
        "• 🪑 Бронь столика — выбрать дату/время, стол и оформить бронь",
        "• 📱 Мини‑приложение — WebApp меню+корзина (нужен https WEBAPP_URL)",
        "",
        "Админские:",
        "• /admin — изменить цены в меню",
        "• /orders — посмотреть последние заказы и менять статусы",
        "• /bookings — посмотреть последние брони и менять статусы",
        "• /admin_help — эта справка",
    ]

    await message.answer("\n".join(lines), reply_markup=main_menu_kb(include_admin=True))


@router.callback_query(F.data == "admin:orders")
async def admin_orders_cb(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not is_admin_user(config, user_id=call.from_user.id if call.from_user else None, chat_id=call.message.chat.id if call.message else None):
        await call.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await _admin_send_orders(call.message, config)
    await call.answer()


@router.callback_query(F.data == "admin:bookings")
async def admin_bookings_cb(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not is_admin_user(config, user_id=call.from_user.id if call.from_user else None, chat_id=call.message.chat.id if call.message else None):
        await call.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await _admin_send_bookings(call.message, config)
    await call.answer()


@router.callback_query(F.data == "admin:back")
async def admin_back(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not is_admin_user(config, user_id=call.from_user.id if call.from_user else None, chat_id=call.message.chat.id if call.message else None):
        await call.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    await call.message.answer("Список позиций:", reply_markup=main_menu_kb(include_admin=True))
    await _admin_send_items(call.message, config)
    await call.answer()


@router.callback_query(F.data.startswith("admin:item:"))
async def admin_open_item(call: CallbackQuery, config: Config) -> None:
    if not is_admin_user(config, user_id=call.from_user.id if call.from_user else None, chat_id=call.message.chat.id if call.message else None):
        await call.answer("Нет доступа", show_alert=True)
        return

    item_id = int(call.data.split(":")[-1])
    item = await fetch_menu_item(config.db_path, item_id)
    if not item:
        await call.answer("Не найдено")
        return

    text = (
        f"{item.category}\n"
        f"<b>{item.title}</b>\n"
        f"Цена: {format_price(item.price_cents)}\n\n"
        f"{item.description}"
    )
    await call.message.answer(text, parse_mode="HTML", reply_markup=admin_item_actions_kb(item.id))
    await call.answer()


@router.callback_query(F.data.startswith("admin:order:"))
async def admin_open_order(call: CallbackQuery, config: Config) -> None:
    if not is_admin_user(config, user_id=call.from_user.id if call.from_user else None, chat_id=call.message.chat.id if call.message else None):
        await call.answer("Нет доступа", show_alert=True)
        return

    order_id = int(call.data.split(":")[-1])
    orders = await fetch_recent_orders(config.db_path, limit=200)
    order = next((o for o in orders if o.id == order_id), None)
    if not order:
        await call.answer("Не найдено")
        return

    items = await fetch_order_items(config.db_path, order_id)
    lines = [
        f"🧾 Заказ #{order.id}",
        f"Тип: {order.type}",
        f"Статус: {order.status}",
        f"Создан: {order.created_at}",
        f"Когда: {order.scheduled_for or 'сейчас'}",
        f"Имя: {order.name}",
        f"Тел: {order.phone}",
        f"Адрес: {order.address or '-'}",
        "",
        "Позиции:",
    ]
    for it in items:
        lines.append(
            f"• {it['title']} ×{it['qty']} = {format_price(it['item_price_cents'] * it['qty'])}"
        )
    lines.append("")
    lines.append(f"Итого: {format_price(order.total_cents)}")
    if order.comment:
        lines.append(f"Комментарий: {order.comment}")

    await call.message.answer("\n".join(lines), reply_markup=admin_order_actions_kb(order.id))
    await call.answer()


@router.callback_query(F.data.startswith("admin:order_status:"))
async def admin_set_order_status(call: CallbackQuery, config: Config) -> None:
    if not is_admin_user(config, user_id=call.from_user.id if call.from_user else None, chat_id=call.message.chat.id if call.message else None):
        await call.answer("Нет доступа", show_alert=True)
        return

    _, _, order_id_s, status = call.data.split(":", 3)
    order_id = int(order_id_s)
    await update_order_status(config.db_path, order_id, status)
    await call.answer("Статус обновлён")


@router.callback_query(F.data.startswith("admin:res:"))
async def admin_open_reservation(call: CallbackQuery, config: Config) -> None:
    if not is_admin_user(config, user_id=call.from_user.id if call.from_user else None, chat_id=call.message.chat.id if call.message else None):
        await call.answer("Нет доступа", show_alert=True)
        return

    res_id = int(call.data.split(":")[-1])
    items = await fetch_recent_reservations(config.db_path, limit=200)
    r = next((x for x in items if x.id == res_id), None)
    if not r:
        await call.answer("Не найдено")
        return

    text = (
        f"🪑 Бронь #{r.id}\n"
        f"Стол: {r.table_code}\n"
        f"Статус: {r.status}\n"
        f"Дата/время: {r.start_at}\n"
        f"Гостей: {r.guests}\n"
        f"Имя: {r.name}\n"
        f"Тел: {r.phone}\n"
        f"Создана: {r.created_at}"
    )
    await call.message.answer(text, reply_markup=admin_booking_actions_kb(r.id))
    await call.answer()


@router.callback_query(F.data.startswith("admin:res_status:"))
async def admin_set_reservation_status(call: CallbackQuery, config: Config) -> None:
    if not is_admin_user(config, user_id=call.from_user.id if call.from_user else None, chat_id=call.message.chat.id if call.message else None):
        await call.answer("Нет доступа", show_alert=True)
        return

    _, _, res_id_s, status = call.data.split(":", 3)
    res_id = int(res_id_s)
    await update_reservation_status(config.db_path, res_id, status)
    await call.answer("Статус обновлён")


@router.callback_query(F.data.startswith("admin:price:"))
async def admin_change_price(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if not is_admin_user(config, user_id=call.from_user.id if call.from_user else None, chat_id=call.message.chat.id if call.message else None):
        await call.answer("Нет доступа", show_alert=True)
        return

    item_id = int(call.data.split(":")[-1])
    item = await fetch_menu_item(config.db_path, item_id)
    if not item:
        await call.answer("Не найдено")
        return

    await state.set_state(AdminFlow.waiting_price)
    await state.update_data(admin_item_id=item_id)
    await call.message.answer(
        f"Введите новую цену для «{item.title}» (например 930 или 930.50):"
    )
    await call.answer()


@router.message(AdminFlow.waiting_price)
async def admin_set_price(message: Message, state: FSMContext, config: Config) -> None:
    if not is_admin_user(config, user_id=message.from_user.id if message.from_user else None, chat_id=message.chat.id):
        await message.answer("Нет доступа.")
        await state.clear()
        return

    data = await state.get_data()
    item_id = data.get("admin_item_id")
    if not item_id:
        await state.clear()
        await message.answer("Контекст потерян. Откройте /admin заново.")
        return

    price_cents = _parse_price_to_cents(message.text or "")
    if price_cents is None:
        await message.answer("Не понял цену. Пример: 930 или 930.50")
        return

    await update_menu_item_price(config.db_path, int(item_id), int(price_cents))
    item = await fetch_menu_item(config.db_path, int(item_id))
    await state.clear()

    if not item:
        await message.answer("Готово.")
        return

    await message.answer(
        f"✅ Цена обновлена: {item.title} — {format_price(item.price_cents)}",
        reply_markup=main_menu_kb(include_admin=True),
    )
