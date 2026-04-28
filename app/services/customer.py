from __future__ import annotations

from dataclasses import dataclass

import logging
from datetime import date
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Customer:
    telegram_id: int
    username: str


@dataclass(frozen=True, slots=True)
class RegisterCustomerResult:
    success: bool
    message: str | None = None
    data: dict[str, Any] | None = None


async def register_customer(
    telegram_id: int,
    name: str,
    phone: str,
    sex: str | None = None,
    email: str | None = None,
    birth_date: date | None = None,
) -> RegisterCustomerResult:
    url = settings.external_api_base_url.rstrip("/") + "/api/gym-register-customer"
    try:
        async with httpx.AsyncClient(timeout=settings.external_api_timeout_sec) as client:
            r = await client.get(
                url,
                params={
                    "telegram_id": telegram_id,
                    "name": name,
                    "phone": phone,
                    "sex": sex,
                    "email": email,
                    "birth_date": birth_date.isoformat() if birth_date else None,
                },
            )
            r.raise_for_status()
            payload = r.json()

            # Support both shapes:
            # 1) {"success": true/false, "message": "...", "data": {...}}
            # 2) direct customer object {...}
            if isinstance(payload, dict) and "success" in payload:
                return RegisterCustomerResult(
                    success=bool(payload.get("success")),
                    message=payload.get("message"),
                    data=payload.get("data") if isinstance(payload.get("data"), dict) else None,
                )

            return RegisterCustomerResult(success=True, data=payload if isinstance(payload, dict) else None)
    except Exception:
        logger.exception("Failed to register customer")
        raise
