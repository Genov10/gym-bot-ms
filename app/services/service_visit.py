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
class StartVisitResult:
    success: bool
    message: str | None = None
    visit: str | None = None


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


async def start_visit(telegram_id: int, service_id: int) -> StartVisitResult:
    url = settings.external_api_base_url.rstrip("/") + "/api/gym-start-visit"
    try:
        async with httpx.AsyncClient(timeout=settings.external_api_timeout_sec) as client:
            r = await client.get(url, params={"telegram_id": telegram_id, "service_id": service_id})
            r.raise_for_status()
            payload: Any = r.json()

        if not isinstance(payload, dict):
            return StartVisitResult(success=False, message="Unexpected response")

        if payload.get("success") is False:
            return StartVisitResult(success=False, message=payload.get("message"))

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
