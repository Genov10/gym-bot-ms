from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CreateOrderResult:
    success: bool
    message: str | None = None
    data: dict[str, Any] | None = None


async def create_order(*, telegram_id: int, service_id: int) -> CreateOrderResult:
    url = settings.external_api_base_url.rstrip("/") + "/api/gym-order-create"
    try:
        async with httpx.AsyncClient(timeout=settings.external_api_timeout_sec) as client:
            logger.info("Calling order create: %s telegram_id=%s service_id=%s", url, telegram_id, service_id)
            r = await client.get(url, params={"telegram_id": telegram_id, "service_id": service_id})
            r.raise_for_status()
            payload: Any = r.json()

        if isinstance(payload, dict) and "success" in payload:
            return CreateOrderResult(
                success=bool(payload.get("success")),
                message=payload.get("message"),
                data=payload.get("data") if isinstance(payload.get("data"), dict) else None,
            )

        return CreateOrderResult(success=True, data=payload if isinstance(payload, dict) else None)
    except Exception:
        logger.exception("Failed to create order telegram_id=%s service_id=%s", telegram_id, service_id)
        return CreateOrderResult(success=False, message="Failed to create order")

