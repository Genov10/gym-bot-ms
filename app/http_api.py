from __future__ import annotations

import html
import logging
from typing import Any

from aiogram import Bot
from fastapi import FastAPI
from pydantic import AliasChoices, BaseModel, Field

from app.telegram_sensitive import PROTECT_CONTENT_KWARGS

logger = logging.getLogger(__name__)


class PaymentResultRequest(BaseModel):
    telegram_id: int = Field(..., ge=1)
    service_name: str = Field(..., validation_alias=AliasChoices("serviceName", "service_name"), min_length=1)
    success: bool = Field(..., validation_alias=AliasChoices("success", "succes"))


class PaymentResultResponse(BaseModel):
    ok: bool
    error: str | None = None


class SubscriptionExpiringItem(BaseModel):
    telegram_id: int = Field(..., ge=1)
    service_id: int = Field(..., ge=1)


class BroadcastResponse(BaseModel):
    total: int
    sent: int
    failed: int
    errors: list[dict[str, Any]] = []


def _payment_result_message(*, success: bool, service_name: str) -> str:
    if success:
        name = html.escape(service_name)
        return (
            "✅ Оплата пройшла успішно\n"
            f"  Ваша послуга \"{name}\" активна \n"
            f"  Вона доспупна у каталозі ваших послуг"
        )
    return "❌ Оплата не пройшла, спробуйте ще раз"


def create_http_app(*, bot: Bot) -> FastAPI:
    app = FastAPI(title="gym-bot-ms http api")
    app.state.bot = bot

    @app.post("/payment-result", response_model=PaymentResultResponse)
    async def payment_result(body: PaymentResultRequest) -> PaymentResultResponse:
        try:
            await bot.send_message(
                body.telegram_id,
                _payment_result_message(success=body.success, service_name=body.service_name),
                **PROTECT_CONTENT_KWARGS,
            )
            return PaymentResultResponse(ok=True)
        except Exception as e:
            logger.exception("Failed to send payment result telegram_id=%s", body.telegram_id)
            return PaymentResultResponse(ok=False, error=str(e))

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
                    **PROTECT_CONTENT_KWARGS,
                )
                sent += 1
            except Exception as e:
                failed += 1
                logger.exception("Failed to send broadcast telegram_id=%s", it.telegram_id)
                errors.append({"telegram_id": it.telegram_id, "service_id": it.service_id, "error": str(e)})

        return BroadcastResponse(total=len(items), sent=sent, failed=failed, errors=errors)

    return app

