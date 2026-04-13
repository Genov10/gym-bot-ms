import logging

from aiogram import Router
from aiogram import F
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from app.db.session import async_session_factory
from app.db.users_repo import register_or_update, set_phone_number
from app.services.external_api import ExternalApiClient

logger = logging.getLogger(__name__)
router = Router(name="start")


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

    await message.answer(
        f"Привіт, {user.first_name or 'атлет'}! Раді тебе бачити!"
    )

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поділитися номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Натисни кнопку нижче",
    )
    await message.answer("Щоб продовжити, поділись, будь ласка, номером телефону.", reply_markup=kb)


@router.message(F.contact)
async def got_contact(message: Message) -> None:
    if message.contact is None:
        return
    phone = message.contact.phone_number
    tg_id = message.from_user.id if message.from_user else None
    logger.info("Got phone number from telegram_id=%s: %s", tg_id, phone)
    if tg_id is not None:
        async with async_session_factory() as session:
            await set_phone_number(session, telegram_id=tg_id, phone_number=phone)
    await message.answer("Дякую! Номер отримано.", reply_markup=ReplyKeyboardRemove())
