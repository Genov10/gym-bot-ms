from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter, Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ChatMemberUpdated, Message

from app.db.session import async_session_factory
from app.db.users_repo import (
    delete_by_telegram_id,
    get_by_telegram_id,
    heal_legacy_verified,
    register_or_update,
)
from app.handlers.start_common import (
    ADMIN_CONTACT_TEXT,
    admin_contact_inline_kb,
    HOME_BUTTON_TEXT,
    menu_kb,
)
from app.services.external_api import ExternalApiClient
from app.services.service_visit import check_customer_exists

logger = logging.getLogger(__name__)
router = Router(name="start_menu")

WELCOME_BACK_TEXT = "З поверненням! Оберіть дію нижче."


async def resolve_registered(*, telegram_id: int, is_registered: bool | None = None) -> bool:
    async with async_session_factory() as session:
        if is_registered is None:
            await heal_legacy_verified(session, telegram_id=telegram_id)
        user = await get_by_telegram_id(session, telegram_id)
        return is_registered if is_registered is not None else (user is not None and user.is_verified)


async def send_menu_to_chat(
    bot: Bot,
    *,
    chat_id: int,
    telegram_id: int,
    text: str,
    is_registered: bool | None = None,
) -> None:
    registered = await resolve_registered(telegram_id=telegram_id, is_registered=is_registered)
    await bot.send_message(chat_id, text, reply_markup=menu_kb(is_registered=registered))


async def send_menu(
    message: Message,
    text: str,
    *,
    telegram_id: int | None = None,
    is_registered: bool | None = None,
) -> None:
    if telegram_id is None:
        if message.from_user is None:
            return
        telegram_id = message.from_user.id

    registered = await resolve_registered(telegram_id=telegram_id, is_registered=is_registered)
    await message.answer(text, reply_markup=menu_kb(is_registered=registered))


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_bot_readded(event: ChatMemberUpdated, bot: Bot) -> None:
    """Користувач розблокував / знову додав бота — одразу відновлюємо меню без /start."""
    user = event.from_user
    if user is None:
        return

    logger.info("Bot re-added/unblocked by telegram_id=%s", user.id)
    try:
        await send_menu_to_chat(
            bot,
            chat_id=event.chat.id,
            telegram_id=user.id,
            text=WELCOME_BACK_TEXT,
        )
    except Exception:
        logger.exception("Failed to restore menu after re-add telegram_id=%s", user.id)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, api: ExternalApiClient) -> None:
    await state.clear()
    if message.from_user is None:
        return

    u = message.from_user

    async with async_session_factory() as session:
        existing = await get_by_telegram_id(session, u.id)

    # Если пользователь уже есть в БД бота — сверяем с основным сервером.
    if existing is not None:
        presence = await check_customer_exists(u.id)
        if presence.exists is False:
            logger.info(
                "Core customer missing for bot user telegram_id=%s; resetting local registration",
                u.id,
            )
            async with async_session_factory() as session:
                await delete_by_telegram_id(session, telegram_id=u.id)
            from app.handlers.start_registration import begin_register

            await begin_register(message, state)
            return

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
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_menu(message, "Чим можу допомогти?")


@router.message(lambda m: m.text == HOME_BUTTON_TEXT)
async def home_button(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_menu(message, "Чим можу допомогти?")


@router.message(F.text == ADMIN_CONTACT_TEXT)
async def admin_contact(message: Message) -> None:
    await message.answer(
        "Натисніть кнопку нижче, щоб відкрити чат з адміністратором:",
        reply_markup=admin_contact_inline_kb(),
    )
