from aiogram import Router

from app.handlers.info import router as info_router
from app.handlers.payment import router as payment_router
from app.handlers.start import router as start_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(start_router)
    root.include_router(payment_router)
    root.include_router(info_router)
    return root
