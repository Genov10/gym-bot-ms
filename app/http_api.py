from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot
from fastapi import FastAPI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SubscriptionExpiringItem(BaseModel):
    telegram_id: int = Field(..., ge=1)
    service_id: int = Field(..., ge=1)


class BroadcastResponse(BaseModel):
    total: int
    sent: int
    failed: int
    errors: list[dict[str, Any]] = []


def create_http_app(*, bot: Bot) -> FastAPI:
    app = FastAPI(title="gym-bot-ms http api")
    app.state.bot = bot

    @app.post("/broadcast/subscription-expiring", response_model=BroadcastResponse)
    async def broadcast_subscription_expiring(items: list[SubscriptionExpiringItem]) -> BroadcastResponse:
        sent = 0
        failed = 0
        errors: list[dict[str, Any]] = []

        for it in items:
            try:
                await bot.send_message(
                    it.telegram_id,
                    f"Нагадування: у вас закінчується абонемент на послугу (service_id={it.service_id}).",
                )
                sent += 1
            except Exception as e:
                failed += 1
                logger.exception("Failed to send broadcast telegram_id=%s", it.telegram_id)
                errors.append({"telegram_id": it.telegram_id, "service_id": it.service_id, "error": str(e)})

        return BroadcastResponse(total=len(items), sent=sent, failed=failed, errors=errors)

    return app

