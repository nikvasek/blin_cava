from __future__ import annotations

from datetime import date
from datetime import datetime
from pathlib import Path
from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.config import Config
from bot.db import create_reservation, fetch_table, fetch_tables, table_is_available
from bot.keyboards import calendar_month_kb, cancel_kb, contact_kb, main_menu_kb, tables_kb
from bot.utils import combine_date_time, is_admin_user, parse_date, parse_time


router = Router(name=__name__)


class BookingFlow(StatesGroup):
    date = State()
    time = State()
    guests = State()
    choose_table = State()
    contact_name = State()
    contact_phone = State()


@router.message(F.text == "🪑 Бронь столика")
async def start_booking(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(BookingFlow.date)
    today = date.today()
    await message.answer(
        "Выберите дату брони (или напишите: 'сегодня', 'завтра', YYYY-MM-DD):",
        reply_markup=cancel_kb(),
    )
    await message.answer(
        "Календарь:",
        reply_markup=calendar_month_kb(today.year, today.month, prefix="booking:cal"),
    )


@router.callback_query(BookingFlow.date, F.data.startswith("booking:cal:nav:"))
async def booking_calendar_nav(call: CallbackQuery) -> None:
    ym = call.data.split(":", 3)[3]
    try:
        y_s, m_s = ym.split("-", 1)
        y, m = int(y_s), int(m_s)
        if m < 1 or m > 12:
            raise ValueError
    except ValueError:
        await call.answer("Не понял месяц")
        return

    await call.message.edit_reply_markup(
        reply_markup=calendar_month_kb(y, m, prefix="booking:cal")
    )
    await call.answer()


@router.callback_query(BookingFlow.date, F.data.startswith("booking:cal:day:"))
async def booking_calendar_day(call: CallbackQuery, state: FSMContext) -> None:
    iso = call.data.split(":", 3)[3]
    d = parse_date(iso)
    if not d:
        await call.answer("Не понял дату")
        return

    await state.update_data(date=d.isoformat())
    await state.set_state(BookingFlow.time)
    await call.message.answer(f"Дата выбрана: {d.isoformat()}\nТеперь введите время (HH:MM), например 19:00")
    await call.answer()


@router.message(BookingFlow.date)
async def booking_date(message: Message, state: FSMContext) -> None:
    d = parse_date(message.text or "")
    if not d:
        await message.answer("Не понял дату. Пример: 2026-02-23")
        return
    await state.update_data(date=d.isoformat())
    await state.set_state(BookingFlow.time)
    await message.answer("На какое время? Напишите HH:MM, например 19:00")


@router.message(BookingFlow.time)
async def booking_time(message: Message, state: FSMContext) -> None:
    t = parse_time(message.text or "")
    if not t:
        await message.answer("Не понял время. Пример: 19:00")
        return
    await state.update_data(time=t.isoformat(timespec="minutes"))
    await state.set_state(BookingFlow.guests)
    await message.answer("Сколько гостей? (числом)")


@router.message(BookingFlow.guests)
async def booking_guests(message: Message, state: FSMContext, config: Config) -> None:
    raw = (message.text or "").strip()
    try:
        guests = int(raw)
    except ValueError:
        await message.answer("Введите число, например 2")
        return
    if guests < 1 or guests > 20:
        await message.answer("Введите количество гостей от 1 до 20")
        return

    data = await state.get_data()
    d = parse_date(data.get("date", ""))
    t = parse_time(data.get("time", ""))
    if not d or not t:
        await state.set_state(BookingFlow.date)
        await message.answer("Давайте заново. Введите дату.")
        return
    start_at = combine_date_time(d, t)
    await state.update_data(guests=guests, start_at=start_at.isoformat(sep=" "))

    tables = await fetch_tables(config.db_path, guests)
    if not tables:
        await message.answer("Нет подходящих столов под это количество гостей.")
        await state.clear()
        return

    buttons: list[tuple[str, str]] = []
    from datetime import timedelta

    window_end = start_at + timedelta(hours=2, minutes=15)
    for tbl in tables:
        ok = await table_is_available(config.db_path, tbl.id, start_at, window_end)
        mark = "✅" if ok else "❌"
        buttons.append((f"{tbl.code} ({tbl.seats}) {mark}", f"booking:table:{tbl.id}:{int(ok)}"))

    plan_path = Path(config.hall_plan_path)
    if plan_path.exists() and plan_path.is_file():
        try:
            plan = BufferedInputFile(plan_path.read_bytes(), filename=plan_path.name)
            await message.answer_photo(
                photo=plan,
                caption="Схема зала (выберите стол):",
            )
        except Exception:
            await message.answer("Выберите стол:")
    else:
        await message.answer("Выберите стол:")

    await state.set_state(BookingFlow.choose_table)
    await message.answer("Доступность помечена ✅/❌", reply_markup=tables_kb(buttons))


@router.callback_query(BookingFlow.choose_table, F.data.startswith("booking:table:"))
async def booking_choose_table(call: CallbackQuery, state: FSMContext) -> None:
    _, _, table_id, ok = call.data.split(":")
    if ok != "1":
        await call.answer("Этот стол уже занят на выбранное время")
        return
    await state.update_data(table_id=int(table_id))
    await state.set_state(BookingFlow.contact_name)
    await call.message.answer("Как к вам обращаться?", reply_markup=cancel_kb())
    await call.answer()


@router.callback_query(F.data == "booking:cancel")
async def booking_cancel(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    await state.clear()
    include_admin = is_admin_user(
        config,
        user_id=call.from_user.id if call.from_user else None,
        chat_id=call.message.chat.id if call.message else None,
    )
    await call.message.answer("Ок, отменил.", reply_markup=main_menu_kb(include_admin=include_admin))
    await call.answer()


@router.message(BookingFlow.contact_name)
async def booking_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Напишите имя чуть подробнее.")
        return
    await state.update_data(name=name)
    await state.set_state(BookingFlow.contact_phone)
    await message.answer("Отправьте номер телефона:", reply_markup=contact_kb())


@router.message(BookingFlow.contact_phone, F.contact)
async def booking_phone_contact(message: Message, state: FSMContext, config: Config) -> None:
    await state.update_data(phone=message.contact.phone_number)
    await _finalize_booking(message, state, config)


@router.message(BookingFlow.contact_phone)
async def booking_phone_text(message: Message, state: FSMContext, config: Config) -> None:
    phone = (message.text or "").strip()
    if len(phone) < 6:
        await message.answer("Похоже на некорректный номер. Попробуйте ещё раз.")
        return
    await state.update_data(phone=phone)
    await _finalize_booking(message, state, config)


async def _finalize_booking(message: Message, state: FSMContext, config: Config) -> None:
    data = await state.get_data()
    start_at_iso = data.get("start_at")
    table_id = data.get("table_id")
    guests = int(data.get("guests", 0))
    if not start_at_iso or not table_id or guests <= 0:
        await message.answer("Не удалось оформить бронь. Попробуйте ещё раз.")
        await state.clear()
        return

    start_at = datetime.fromisoformat(start_at_iso)
    reservation_id = await create_reservation(
        config.db_path,
        user_id=message.from_user.id,
        table_id=int(table_id),
        start_at=start_at,
        guests=guests,
        name=str(data.get("name", "")),
        phone=str(data.get("phone", "")),
    )

    await message.answer(
        f"✅ Бронь оформлена. Номер: {reservation_id}",
        reply_markup=main_menu_kb(
            include_admin=is_admin_user(
                config,
                user_id=message.from_user.id if message.from_user else None,
                chat_id=message.chat.id,
            )
        ),
    )

    if config.admin_chat_id:
        table = await fetch_table(config.db_path, int(table_id))
        table_label = table.code if table else f"id={table_id}"
        text = (
            f"🪑 Новая бронь #{reservation_id}\n"
            f"Дата/время: {start_at}\n"
            f"Гостей: {guests}\n"
            f"Стол: {table_label}\n"
            f"Имя: {data.get('name')}\n"
            f"Тел: {data.get('phone')}"
        )
        try:
            await message.bot.send_message(config.admin_chat_id, text)
        except Exception:
            pass

    await state.clear()
