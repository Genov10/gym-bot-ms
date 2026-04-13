import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.db import init_db
from app.handlers import setup_routers
from app.middlewares import ApiMiddleware
from app.services.external_api import ExternalApiClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()
    api = ExternalApiClient()
    bot = Bot(token=settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.middleware(ApiMiddleware(api))
    dp.include_router(setup_routers())

    try:
        await dp.start_polling(bot)
    finally:
        await api.aclose()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
