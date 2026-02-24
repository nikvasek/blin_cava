from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.keyboards import open_webapp_kb


router = Router(name=__name__)


@router.callback_query(F.data == "noop")
async def noop_callback(call: CallbackQuery) -> None:
    # Used for disabled inline buttons (calendar headers, empty cells, etc.)
    try:
        await call.answer()
    except Exception:
        return


@router.message(CommandStart())
async def start(message: Message, config: Config) -> None:
    if not config.webapp_url:
        await message.answer(
            "Мини‑приложение пока не настроено.\n"
            "Укажите WEBAPP_URL (https) в .env и перезапустите бота."
        )
        return
    await message.answer(
        "Откройте мини‑приложение меню:",
        reply_markup=open_webapp_kb(config.webapp_url),
    )


@router.message(Command("app"))
async def open_app(message: Message, config: Config) -> None:
    if not config.webapp_url:
        await message.answer(
            "Мини‑приложение пока не настроено.\n"
            "Укажите WEBAPP_URL (https) в .env и перезапустите бота."
        )
        return
    await message.answer(
        "Откройте мини‑приложение меню:",
        reply_markup=open_webapp_kb(config.webapp_url),
    )
