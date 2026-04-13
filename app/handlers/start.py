import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from app.db.session import async_session_factory
from app.db.users_repo import register_or_update
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
        f"Привет, {user.first_name or 'атлет'}! Вы зарегистрированы. "
        f"ID в Telegram: {user.telegram_id}."
    )
