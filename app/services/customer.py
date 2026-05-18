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
    already_exists: bool = False


def _response_payload(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _error_message(response: httpx.Response, payload: dict[str, Any]) -> str:
    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        return message

    if response.status_code == 422:
        errors = payload.get("errors")
        if isinstance(errors, dict):
            parts: list[str] = []
            for field, items in errors.items():
                if isinstance(items, list) and items:
                    parts.append(f"{field}: {items[0]}")
            if parts:
                return "; ".join(parts)

    return f"Помилка сервера (HTTP {response.status_code})"


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
            response = await client.get(url, params=params)
            payload = _response_payload(response)

            if response.status_code == 409:
                return RegisterCustomerResult(
                    success=False,
                    message=_error_message(response, payload),
                    data=payload.get("data") if isinstance(payload.get("data"), dict) else None,
                    already_exists=True,
                )

            if isinstance(payload, dict) and "success" in payload:
                return RegisterCustomerResult(
                    success=bool(payload.get("success")),
                    message=payload.get("message") if isinstance(payload.get("message"), str) else None,
                    data=payload.get("data") if isinstance(payload.get("data"), dict) else None,
                )

            if response.is_success:
                return RegisterCustomerResult(success=True, data=payload or None)

            logger.warning(
                "Register customer failed telegram_id=%s status=%s payload=%s",
                telegram_id,
                response.status_code,
                payload,
            )
            return RegisterCustomerResult(
                success=False,
                message=_error_message(response, payload),
            )
    except httpx.RequestError:
        logger.exception("Register customer network error telegram_id=%s", telegram_id)
        return RegisterCustomerResult(
            success=False,
            message="Не вдалося з'єднатися з сервером. Спробуйте пізніше.",
        )
