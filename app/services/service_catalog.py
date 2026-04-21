from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass(frozen=True, slots=True)
class ServiceItem:
    code: str
    title: str
    price_uah: int


async def list_services_mock() -> list[ServiceItem]:
    """
    Временная реализация каталога услуг.

    Сейчас: пытаемся получить услуги с внешнего API, а если оно недоступно/формат неожиданный —
    возвращаем мок.
    """
    url = settings.external_api_base_url.rstrip("/") + "/api/gym-services"
    try:
        async with httpx.AsyncClient(timeout=settings.external_api_timeout_sec) as client:
            r = await client.get(url)
            r.raise_for_status()
            payload = r.json()

        data = payload.get("data", payload)
        if not isinstance(data, list):
            raise ValueError("Unexpected catalog payload shape")

        items: list[ServiceItem] = []
        for svc in data:
            items.append(
                ServiceItem(
                    code=str(svc.get("id") or svc.get("code")),
                    title=str(svc.get("name") or svc.get("title")),
                    price_uah=int(svc.get("price") or svc.get("price_uah") or 0),
                )
            )
        if items:
            return items
    except Exception:
        # fallback to mock below
        pass

    return None

