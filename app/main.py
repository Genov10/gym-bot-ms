import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
import uvicorn

from app.config import settings
from app.db.migrate import upgrade_head
from app.handlers import setup_routers
from app.http_api import create_http_app
from app.middlewares import ApiMiddleware
from app.services.external_api import ExternalApiClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    # Auto-apply DB migrations on startup
    await asyncio.to_thread(upgrade_head)
    api = ExternalApiClient()
    bot = Bot(token=settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(ApiMiddleware(api))
    dp.include_router(setup_routers())

    http_app = create_http_app(bot=bot)
    http_config = uvicorn.Config(
        http_app,
        host=settings.bot_http_host,
        port=settings.bot_http_port,
        log_level="info",
        loop="asyncio",
    )
    http_server = uvicorn.Server(http_config)
    http_task = asyncio.create_task(http_server.serve())

    try:
        await dp.start_polling(bot)
    finally:
        http_server.should_exit = True
        try:
            await http_task
        except Exception:
            logger.exception("HTTP server shutdown error")
        await api.aclose()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
