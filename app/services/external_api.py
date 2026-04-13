"""HTTP client for the external backend: user sync, payment requisites, etc."""

from typing import Any

import httpx

from app.config import settings


class ExternalApiClient:
    def __init__(self) -> None:
        headers: dict[str, str] = {"Accept": "application/json"}
        if settings.external_api_key:
            headers["Authorization"] = f"Bearer {settings.external_api_key}"
        self._client = httpx.AsyncClient(
            base_url=settings.external_api_base_url.rstrip("/"),
            headers=headers,
            timeout=settings.external_api_timeout_sec,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def upsert_user(self, telegram_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Create or update user profile on the external service."""
        r = await self._client.put(f"/api/users/{telegram_id}", json=payload)
        r.raise_for_status()
        return r.json()

    async def get_payment_requisites(self, telegram_id: int) -> dict[str, Any]:
        """Fetch payment details (IBAN, card, etc.) for the user."""
        r = await self._client.get(f"/api/users/{telegram_id}/payment-requisites")
        r.raise_for_status()
        return r.json()
