from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CustomerGymService:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class CustomerGymServiceInfo:
    service_name: str
    description: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    lefted_visits_amount: int | None = None
    can_be_frosen: bool = False


@dataclass(frozen=True, slots=True)
class FreezePreview:
    service_name: str
    rules: tuple[str, ...]
    can_be_frosen: bool = False


@dataclass(frozen=True, slots=True)
class FreezeConfirmResult:
    success: bool
    message: str | None = None
    service_name: str | None = None


@dataclass(frozen=True, slots=True)
class StartVisitResult:
    success: bool
    message: str | None = None
    visit: str | None = None
    code: int | None = None


TOO_MANY_UNFINISHED_VISITS_CODE = 15
TOO_MANY_UNFINISHED_VISITS_MESSAGE = (
    "Ви намагались зайти до залу більше трьох разів. Зверніться до адміністратора"
)


async def get_service_visit(telegram_id: int) -> list[CustomerGymService] | None:
    url = settings.external_api_base_url.rstrip("/") + "/api/gym-get-customer-gym-services"
    try:
        async with httpx.AsyncClient(timeout=settings.external_api_timeout_sec) as client:
            logger.info("Calling customer services: %s telegram_id=%s", url, telegram_id)
            r = await client.get(url, params={"telegram_id": telegram_id})
            r.raise_for_status()
            payload: Any = r.json()

        if not isinstance(payload, dict):
            raise ValueError("Unexpected payload type")

        if payload.get("success") is False:
            logger.info("Customer services fetch failed: %s", payload.get("message"))
            return None

        data = payload.get("data")
        if not isinstance(data, list):
            return None

        items: list[CustomerGymService] = []
        for row in data:
            if not isinstance(row, dict):
                continue
            try:
                items.append(CustomerGymService(id=int(row["id"]), name=str(row["name"])))
            except Exception:
                continue

        return items or None
    except Exception:
        logger.exception("Failed to fetch customer gym services for telegram_id=%s", telegram_id)
        return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def get_customer_gym_service_info(
    telegram_id: int,
    service_id: int,
) -> CustomerGymServiceInfo | None:
    url = settings.external_api_base_url.rstrip("/") + "/api/gym-get-customer-gym-service-info"
    try:
        async with httpx.AsyncClient(timeout=settings.external_api_timeout_sec) as client:
            logger.info(
                "Calling customer service info: %s telegram_id=%s service_id=%s",
                url,
                telegram_id,
                service_id,
            )
            r = await client.get(url, params={"telegram_id": telegram_id, "service_id": service_id})
            r.raise_for_status()
            payload: Any = r.json()

        if not isinstance(payload, dict) or payload.get("success") is False:
            logger.info("Customer service info fetch failed: %s", payload)
            return None

        data = payload.get("data")
        if not isinstance(data, dict):
            return None

        service_name = _optional_str(data.get("service_name"))
        if not service_name:
            return None

        return CustomerGymServiceInfo(
            service_name=service_name,
            description=_optional_str(data.get("description")),
            date_from=_optional_str(data.get("date_from")),
            date_to=_optional_str(data.get("date_to")),
            lefted_visits_amount=_optional_int(data.get("lefted_visits_amount")),
            can_be_frosen=bool(data.get("can_be_frosen")),
        )
    except Exception:
        logger.exception(
            "Failed to fetch customer gym service info telegram_id=%s service_id=%s",
            telegram_id,
            service_id,
        )
        return None


async def get_freeze_preview(telegram_id: int, service_id: int) -> FreezePreview | None:
    url = settings.external_api_base_url.rstrip("/") + "/api/gym-freeze-preview"
    try:
        async with httpx.AsyncClient(timeout=settings.external_api_timeout_sec) as client:
            logger.info(
                "Calling freeze preview: %s telegram_id=%s service_id=%s",
                url,
                telegram_id,
                service_id,
            )
            r = await client.get(url, params={"telegram_id": telegram_id, "service_id": service_id})
            r.raise_for_status()
            payload: Any = r.json()

        if not isinstance(payload, dict) or payload.get("success") is False:
            logger.info("Freeze preview failed: %s", payload)
            return None

        data = payload.get("data")
        if not isinstance(data, dict):
            return None

        service_name = _optional_str(data.get("service_name"))
        if not service_name:
            return None

        raw_rules = data.get("rules")
        rules: list[str] = []
        if isinstance(raw_rules, list):
            for item in raw_rules:
                text = _optional_str(item)
                if text:
                    rules.append(text)

        return FreezePreview(
            service_name=service_name,
            rules=tuple(rules),
            can_be_frosen=bool(data.get("can_be_frosen")),
        )
    except Exception:
        logger.exception(
            "Failed to fetch freeze preview telegram_id=%s service_id=%s",
            telegram_id,
            service_id,
        )
        return None


async def confirm_freeze(telegram_id: int, service_id: int) -> FreezeConfirmResult:
    url = settings.external_api_base_url.rstrip("/") + "/api/gym-freeze-confirm"
    try:
        async with httpx.AsyncClient(timeout=settings.external_api_timeout_sec) as client:
            logger.info(
                "Calling freeze confirm: %s telegram_id=%s service_id=%s",
                url,
                telegram_id,
                service_id,
            )
            r = await client.get(url, params={"telegram_id": telegram_id, "service_id": service_id})
            try:
                payload: Any = r.json()
            except Exception:
                payload = None

        if isinstance(payload, dict) and payload.get("success") is False:
            return FreezeConfirmResult(success=False, message=_optional_str(payload.get("message")))

        if not r.is_success or not isinstance(payload, dict):
            return FreezeConfirmResult(success=False, message="Не вдалося заморозити абонемент.")

        return FreezeConfirmResult(success=True, message=_optional_str(payload.get("message")))
    except Exception:
        logger.exception(
            "Failed to confirm freeze telegram_id=%s service_id=%s",
            telegram_id,
            service_id,
        )
        return FreezeConfirmResult(success=False, message="Не вдалося заморозити абонемент.")


async def start_visit(telegram_id: int, service_id: int) -> StartVisitResult:
    url = settings.external_api_base_url.rstrip("/") + "/api/gym-start-visit"
    try:
        async with httpx.AsyncClient(timeout=settings.external_api_timeout_sec) as client:
            r = await client.get(url, params={"telegram_id": telegram_id, "service_id": service_id})
            try:
                payload: Any = r.json()
            except Exception:
                payload = None

        if isinstance(payload, dict) and payload.get("success") is False:
            code = payload.get("code")
            code_int = code if isinstance(code, int) else None
            if code_int == TOO_MANY_UNFINISHED_VISITS_CODE:
                return StartVisitResult(
                    success=False,
                    code=code_int,
                    message=TOO_MANY_UNFINISHED_VISITS_MESSAGE,
                )
            return StartVisitResult(
                success=False,
                code=code_int,
                message=payload.get("message"),
            )

        if not r.is_success:
            return StartVisitResult(success=False, message="Неможливо почати тренування")

        if not isinstance(payload, dict):
            return StartVisitResult(success=False, message="Unexpected response")

        data = payload.get("data")
        if not isinstance(data, dict):
            return StartVisitResult(success=False, message="Unexpected response")

        visit = None
        if isinstance(data.get("visit"), str):
            visit = data["visit"]

        return StartVisitResult(success=True, message=payload.get("message"), visit=visit)
    except Exception:
        logger.exception("Failed to start visit telegram_id=%s service_id=%s", telegram_id, service_id)
        return StartVisitResult(success=False, message="Неможливо почати тренування")


@dataclass(frozen=True, slots=True)
class FinishVisitResult:
    success: bool
    message: str | None = None


async def finish_visit(telegram_id: int) -> FinishVisitResult:
    url = settings.external_api_base_url.rstrip("/") + "/api/gym-finish-visit"
    try:
        async with httpx.AsyncClient(timeout=settings.external_api_timeout_sec) as client:
            r = await client.get(url, params={"telegram_id": telegram_id})
            r.raise_for_status()
            payload: Any = r.json()

        if isinstance(payload, dict) and payload.get("success") is False:
            return FinishVisitResult(success=False, message=payload.get("message"))

        return FinishVisitResult(
            success=True,
            message=payload.get("message") if isinstance(payload, dict) else None,
        )
    except Exception:
        logger.exception("Failed to finish visit telegram_id=%s", telegram_id)
        return FinishVisitResult(success=False, message="Неможливо завершити тренування")
