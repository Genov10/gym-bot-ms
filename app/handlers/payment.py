import html
import json
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.external_api import ExternalApiClient

logger = logging.getLogger(__name__)
router = Router(name="payment")


@router.message(Command("requisites", "реквизиты"))
async def cmd_requisites(message: Message, api: ExternalApiClient) -> None:
    if message.from_user is None:
        return
    try:
        data = await api.get_payment_requisites(message.from_user.id)
    except Exception:
        logger.exception("payment requisites fetch failed")
        await message.answer("Не удалось получить реквизиты. Попробуйте позже.")
        return
    text = html.escape(json.dumps(data, ensure_ascii=False, indent=2))
    await message.answer(f"<pre>{text}</pre>")
