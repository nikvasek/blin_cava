from __future__ import annotations

import calendar
from datetime import date

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_menu_kb(*, include_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📱 Открыть меню"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def open_webapp_kb(url: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📱 Открыть меню", web_app=WebAppInfo(url=url)))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def admin_items_kb(items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for item_id, label in items:
        b.add(
            InlineKeyboardButton(
                text=label[:64],
                callback_data=f"admin:item:{int(item_id)}",
            )
        )
    b.adjust(1)
    return b.as_markup()


def admin_item_actions_kb(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить цену", callback_data=f"admin:price:{int(item_id)}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")],
        ]
    )


def admin_orders_kb(orders: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for order_id, label in orders:
        b.add(
            InlineKeyboardButton(
                text=label[:64],
                callback_data=f"admin:order:{int(order_id)}",
            )
        )
    b.adjust(1)
    return b.as_markup()


def admin_order_actions_kb(order_id: int) -> InlineKeyboardMarkup:
    statuses = [
        ("new", "🆕 Новый"),
        ("cooking", "🍳 Готовится"),
        ("ready", "✅ Готов"),
        ("courier", "🛵 Курьер"),
        ("done", "🏁 Завершён"),
        ("canceled", "❌ Отменён"),
    ]
    rows = [
        [
            InlineKeyboardButton(
                text=label,
                callback_data=f"admin:order_status:{int(order_id)}:{code}",
            )
        ]
        for code, label in statuses
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:orders")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_bookings_kb(items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for reservation_id, label in items:
        b.add(
            InlineKeyboardButton(
                text=label[:64],
                callback_data=f"admin:res:{int(reservation_id)}",
            )
        )
    b.adjust(1)
    return b.as_markup()


def admin_booking_actions_kb(reservation_id: int) -> InlineKeyboardMarkup:
    statuses = [
        ("pending", "🕒 Ожидает"),
        ("confirmed", "✅ Подтверждена"),
        ("seated", "🪑 Посадили"),
        ("no_show", "🚫 No-show"),
        ("canceled", "❌ Отменена"),
    ]
    rows = [
        [
            InlineKeyboardButton(
                text=label,
                callback_data=f"admin:res_status:{int(reservation_id)}:{code}",
            )
        ]
        for code, label in statuses
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:bookings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


def contact_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📱 Отправить номер", request_contact=True))
    builder.add(KeyboardButton(text="❌ Отмена"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def categories_kb(categories: list[str], *, for_order: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    prefix = "order_cat" if for_order else "menu_cat"
    for cat in categories:
        b.add(InlineKeyboardButton(text=cat, callback_data=f"{prefix}:{cat}"))
    b.adjust(2)
    return b.as_markup()


def items_kb(item_ids: list[int], *, for_order: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if for_order:
        for item_id in item_ids:
            b.row(
                InlineKeyboardButton(text=f"➖ {item_id}", callback_data=f"cart:dec:{item_id}"),
                InlineKeyboardButton(text=f"➕ {item_id}", callback_data=f"cart:inc:{item_id}"),
            )
        b.row(InlineKeyboardButton(text="🧺 Корзина", callback_data="cart:view"))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back"))
    return b.as_markup()


def order_items_kb(
    items: list[tuple[int, str]],
    *,
    cart: dict[str, int] | None = None,
) -> InlineKeyboardMarkup:
    """Order keyboard with +/− around the item title.

    Each row: ➖ | Title ×N | ➕
    """

    cart = cart or {}
    b = InlineKeyboardBuilder()
    for item_id, title in items:
        qty = int(cart.get(str(item_id), 0))
        center = f"{title}"
        if qty > 0:
            center = f"{title} ×{qty}"
        b.row(
            InlineKeyboardButton(text="➖", callback_data=f"cart:dec:{item_id}"),
            InlineKeyboardButton(text=center[:64], callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"cart:inc:{item_id}"),
        )

    b.row(InlineKeyboardButton(text="🧺 Корзина", callback_data="cart:view"))
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back"))
    return b.as_markup()


def order_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚶 Самовывоз", callback_data="order:type:pickup"),
                InlineKeyboardButton(text="🛵 Доставка", callback_data="order:type:delivery"),
            ]
        ]
    )


def yes_no_kb(yes_cb: str, no_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=yes_cb),
                InlineKeyboardButton(text="❌ Нет", callback_data=no_cb),
            ]
        ]
    )


def tables_kb(table_buttons: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for text, cb in table_buttons:
        b.add(InlineKeyboardButton(text=text, callback_data=cb))
    b.adjust(2)
    b.row(InlineKeyboardButton(text="❌ Отмена", callback_data="booking:cancel"))
    return b.as_markup()


def calendar_month_kb(year: int, month: int, *, prefix: str) -> InlineKeyboardMarkup:
    """Simple inline calendar.

    Callback data:
    - {prefix}:day:YYYY-MM-DD
    - {prefix}:nav:YYYY-MM
    - noop
    """

    today = date.today()
    month_cal = calendar.monthcalendar(year, month)
    month_name = f"{calendar.month_name[month]} {year}"

    b = InlineKeyboardBuilder()

    # Header with navigation
    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_y, next_m = (year + 1, 1) if month == 12 else (year, month + 1)
    b.row(
        InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}:nav:{prev_y:04d}-{prev_m:02d}"),
        InlineKeyboardButton(text=month_name, callback_data="noop"),
        InlineKeyboardButton(text="➡️", callback_data=f"{prefix}:nav:{next_y:04d}-{next_m:02d}"),
    )

    # Weekday header (Mon..Sun)
    for w in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
        b.add(InlineKeyboardButton(text=w, callback_data="noop"))
    b.adjust(7)

    # Days
    for week in month_cal:
        row: list[InlineKeyboardButton] = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
                continue

            d = date(year, month, day)
            if d < today:
                row.append(InlineKeyboardButton(text=f"{day}", callback_data="noop"))
            else:
                row.append(
                    InlineKeyboardButton(
                        text=f"{day}",
                        callback_data=f"{prefix}:day:{d.isoformat()}",
                    )
                )
        b.row(*row)

    b.row(InlineKeyboardButton(text="❌ Отмена", callback_data="booking:cancel"))
    return b.as_markup()
