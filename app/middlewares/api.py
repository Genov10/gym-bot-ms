from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.services.external_api import ExternalApiClient


class ApiMiddleware(BaseMiddleware):
    def __init__(self, api: ExternalApiClient) -> None:
        self._api = api

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["api"] = self._api
        return await handler(event, data)
