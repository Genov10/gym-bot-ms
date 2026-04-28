from aiogram import Router

from app.handlers.start_catalog import router as start_catalog_router
from app.handlers.start_menu import router as start_menu_router
from app.handlers.start_registration import router as start_registration_router
from app.handlers.start_visit import router as start_visit_router

router = Router(name="start")
router.include_router(start_menu_router)
router.include_router(start_registration_router)
router.include_router(start_catalog_router)
router.include_router(start_visit_router)
