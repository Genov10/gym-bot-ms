from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.db.session import async_session_factory
from app.db.users_repo import clear_active_visit_if_expired, get_by_telegram_id, is_active_visit, register_or_update
from app.handlers.start_common import HOME_BUTTON_TEXT, home_kb, menu_kb
from app.services.external_api import ExternalApiClient

logger = logging.getLogger(__name__)
router = Router(name="start_menu")


async def send_menu(message: Message, text: str, *, telegram_id: int | None = None) -> None:
    if telegram_id is None:
        if message.from_user is None:
            return
        telegram_id = message.from_user.id

    async with async_session_factory() as session:
        await clear_active_visit_if_expired(session, telegram_id=telegram_id)
        user = await get_by_telegram_id(session, telegram_id)
        registered = user is not None and user.phone_number is not None
        active = await is_active_visit(session, telegram_id=telegram_id)

    await message.answer(text, reply_markup=menu_kb(is_registered=registered, has_active_visit=active))
    # оставляем HOME кнопку как отдельную reply-клавиатуру только если нужно явно


@router.message(CommandStart())
async def cmd_start(message: Message, api: ExternalApiClient) -> None:
    if message.from_user is None:
        return

    u = message.from_user
    async with async_session_factory() as session:
        user = await register_or_update(
            session,
            telegram_id=u.id,
            username=u.username,
            first_name=u.first_name,
        )

    payload = {
        "telegram_id": u.id,
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "language_code": u.language_code,
    }
    try:
        await api.upsert_user(u.id, payload)
    except Exception:
        logger.exception("external API upsert failed for telegram_id=%s", u.id)

    await send_menu(
        message,
        f"Привіт, {user.first_name or 'атлет'}! Я твій помічник у залі. Чи можу допомогти?",
        telegram_id=u.id,
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await send_menu(message, "Чим можу допомогти?")


@router.message(lambda m: m.text == HOME_BUTTON_TEXT)
async def home_button(message: Message) -> None:
    await send_menu(message, "Чим можу допомогти?")

