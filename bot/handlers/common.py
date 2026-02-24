from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.keyboards import main_menu_kb, open_webapp_kb
from bot.utils import is_admin_user


router = Router(name=__name__)


@router.callback_query(F.data == "noop")
async def noop_callback(call: CallbackQuery) -> None:
    # Used for disabled inline buttons (calendar headers, empty cells, etc.)
    try:
        await call.answer()
    except Exception:
        return


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, config: Config) -> None:
    await state.clear()
    include_admin = is_admin_user(
        config,
        user_id=message.from_user.id if message.from_user else None,
        chat_id=message.chat.id,
    )
    await message.answer(
        "Привет! Я бот кафе.\n\nВыберите действие:",
        reply_markup=main_menu_kb(include_admin=include_admin),
    )


@router.message(Command("app"))
@router.message(F.text == "📱 Мини‑приложение")
async def open_app(message: Message, config: Config) -> None:
    include_admin = is_admin_user(
        config,
        user_id=message.from_user.id if message.from_user else None,
        chat_id=message.chat.id,
    )
    if not config.webapp_url:
        await message.answer(
            "Мини‑приложение пока не настроено.\n"
            "Укажите WEBAPP_URL (https) в .env и перезапустите бота.",
            reply_markup=main_menu_kb(include_admin=include_admin),
        )
        return
    await message.answer(
        "Откройте мини‑приложение меню:",
        reply_markup=open_webapp_kb(config.webapp_url),
    )


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def cancel(message: Message, state: FSMContext, config: Config) -> None:
    await state.clear()
    include_admin = is_admin_user(
        config,
        user_id=message.from_user.id if message.from_user else None,
        chat_id=message.chat.id,
    )
    await message.answer("Ок, отменил.", reply_markup=main_menu_kb(include_admin=include_admin))
