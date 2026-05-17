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
    *,
    first_name: str,
    lastname: str,
    phone: str,
    username: str | None = None,
    sex: str | None = None,
    email: str | None = None,
    birth_date: date | None = None,
) -> RegisterCustomerResult:
    """Register customer on gym-core-ms (GET /api/gym-register-customer).

    Backend expects: name, lastname, username, sex, telegram_id, phone, email.
    Note: birth_date is collected in the bot but not stored by the API yet.
    """
    url = settings.external_api_base_url.rstrip("/") + "/api/gym-register-customer"
    params: dict[str, str] = {
        "telegram_id": str(telegram_id),
        "name": first_name,
        "lastname": lastname,
        "phone": phone,
    }
    if username:
        params["username"] = username.lstrip("@")
    if sex:
        params["sex"] = sex
    if email:
        params["email"] = email

    if birth_date is not None:
        logger.debug("birth_date=%s is not sent to gym-register-customer (API has no field)", birth_date)

    try:
        async with httpx.AsyncClient(timeout=settings.external_api_timeout_sec) as client:
            logger.info("Register customer request telegram_id=%s params_keys=%s", telegram_id, sorted(params))
            r = await client.get(url, params=params)
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
        return RegisterCustomerResult(success=False, message="Не вдалося з'єднатися з сервером. Спробуйте пізніше.")
