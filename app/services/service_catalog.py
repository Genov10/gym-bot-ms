from __future__ import annotations

from dataclasses import dataclass

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ServiceItem:
    code: str
    title: str
    price_uah: int
    description: str
    sale_from: int | None = None


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


_STRIKE_PAD = ""


def _strikethrough_plain(text: str) -> str:
    """Зачёркивание в кнопках (без HTML). U+0335 — лінія по центру; паддинг зліва/справа."""
    extended = f"{_STRIKE_PAD}{text}{_STRIKE_PAD}"
    return "".join(f"{char}\u0335" for char in extended)


def format_service_price_plain(item: ServiceItem) -> str:
    if item.sale_from is not None and item.sale_from != item.price_uah:
        return f"{_strikethrough_plain(str(item.sale_from))} {item.price_uah} ₴"
    return f"{item.price_uah} ₴"


def format_service_price_html(item: ServiceItem) -> str:
    if item.sale_from is not None and item.sale_from != item.price_uah:
        return f"<s>{item.sale_from}</s> <b>{item.price_uah}</b> ₴"
    return f"<b>{item.price_uah}</b> ₴"


async def get_service_catalog(telegram_id: int) -> list[ServiceItem] | None:
    """
    Каталог послуг зовнішнього API (потрібен telegram_id).
    Якщо API недоступно/формат неочікуваний/послуг немає — повертає None.
    """
    url = settings.external_api_base_url.rstrip("/") + "/api/gym-services"
    try:
        async with httpx.AsyncClient(timeout=settings.external_api_timeout_sec) as client:
            r = await client.get(url, params={"telegram_id": telegram_id})
            r.raise_for_status()
            payload = r.json()

        data = payload.get("data", payload)
        if not isinstance(data, list):
            raise ValueError("Unexpected catalog payload shape")

        items: list[ServiceItem] = []
        for svc in data:
            price_uah = _to_int(svc.get("sale")) or _to_int(svc.get("price")) or _to_int(svc.get("price_uah")) or 0
            items.append(
                ServiceItem(
                    code=str(svc.get("id") or svc.get("code")),
                    title=str(svc.get("name") or svc.get("title")),
                    price_uah=price_uah,
                    description=str(svc.get("description") or ""),
                    sale_from=_to_int(svc.get("sale_from")),
                )
            )
        if items:
            return items
    except Exception:
        logger.exception("Failed to fetch service catalog telegram_id=%s", telegram_id)

    return None

