from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ServiceItem:
    code: str
    title: str
    price_uah: int


async def list_services_mock() -> list[ServiceItem]:
    # TODO: заменить на вызов внешнего API
    return [
        ServiceItem(code="day_pass", title="Разовий вхід (Day Pass)", price_uah=250),
        ServiceItem(code="month", title="Абонемент на місяць", price_uah=1200),
        ServiceItem(code="trainer", title="Персональне тренування", price_uah=600),
    ]

