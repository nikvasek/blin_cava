from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.db import fetch_categories, fetch_menu_items
from bot.keyboards import categories_kb, main_menu_kb
from bot.utils import format_price, is_admin_user


router = Router(name=__name__)


@router.message(F.text == "🍽 Меню")
async def show_menu_root(message: Message, config: Config) -> None:
    categories = await fetch_categories(config.db_path)
    if not categories:
        include_admin = is_admin_user(
            config,
            user_id=message.from_user.id if message.from_user else None,
            chat_id=message.chat.id,
        )
        await message.answer("Меню пустое.", reply_markup=main_menu_kb(include_admin=include_admin))
        return

    await message.answer(
        "Категории:",
        reply_markup=None,
    )
    await message.answer(
        "Выберите категорию:",
        reply_markup=categories_kb(categories, for_order=False),
    )


@router.callback_query(F.data.startswith("menu_cat:"))
async def show_menu_category(call: CallbackQuery, config: Config) -> None:
    category = call.data.split(":", 1)[1]
    items = await fetch_menu_items(config.db_path, category)
    if not items:
        await call.message.answer("В этой категории пока нет позиций.")
        await call.answer()
        return

    cat = html.escape(category)
    lines: list[str] = [f"<b>{cat}</b>", ""]
    for it in items:
        title = html.escape(it.title)
        desc = html.escape(it.description)
        price = html.escape(format_price(it.price_cents))
        lines.append(f"{title} — {price}")
        if desc:
            lines.append(desc)
        lines.append("")

    await call.message.answer("\n".join(lines).rstrip(), parse_mode="HTML")
    await call.answer()
