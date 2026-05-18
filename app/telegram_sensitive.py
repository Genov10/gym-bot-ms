"""Telegram flags and helpers for sensitive content (QR, payment notices, etc.)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiogram import Bot

logger = logging.getLogger(__name__)

# No forwarding/saving; on supported clients reduces screenshot sharing.
PROTECT_CONTENT_KWARGS: dict[str, Any] = {"protect_content": True}

# Photo is blurred until the user taps to reveal.
SPOILER_PHOTO_KWARGS: dict[str, Any] = {**PROTECT_CONTENT_KWARGS, "has_spoiler": True}


def schedule_message_delete(*, bot: Bot, chat_id: int, message_id: int, delay_sec: float) -> None:
    """Delete a message after delay (best-effort; does not block screenshots)."""
    if delay_sec <= 0:
        return

    async def _run() -> None:
        await asyncio.sleep(delay_sec)
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception:
            logger.exception("Failed to delete ephemeral message chat_id=%s message_id=%s", chat_id, message_id)

    asyncio.create_task(_run())
