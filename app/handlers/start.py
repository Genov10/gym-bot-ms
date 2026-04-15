import logging

from aiogram import Router
from aiogram import F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from app.db.session import async_session_factory
from app.db.users_repo import register_or_update, set_phone_number
from app.services.external_api import ExternalApiClient
from app.services.service_catalog import list_services_mock

logger = logging.getLogger(__name__)
router = Router(name="start")

HOME_BUTTON_TEXT = "🏠 Головне меню"

MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Реєстрація", callback_data="action:register"),
            InlineKeyboardButton(text="Каталог", callback_data="action:catalog"),
        ]
    ]
)

def _home_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=HOME_BUTTON_TEXT)]],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Обери дію",
    )


async def _send_menu(message: Message, text: str) -> None:
    await message.answer(text, reply_markup=MENU_KB)
    # Постоянная кнопка под полем ввода
    await message.answer("", reply_markup=_home_kb())


async def _send_catalog(message: Message) -> None:
    services = await list_services_mock()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{s.title} — {s.price_uah} ₴",
                    callback_data=f"service:{s.code}",
                )
            ]
            for s in services
        ]
    )
    await message.answer("Каталог послуг. Обери послугу зі списку.", reply_markup=kb)


@router.message(CommandStart())
async def cmd_start(message: Message, api: ExternalApiClient) -> None:
    if message.from_user is None:
        return

    u = message.from_user
    async with async_session_factory() as session:
        user = await register_or_update(
            session,
            telegram_id=u.id,
            username=u.username,
            first_name=u.first_name,
        )

    payload = {
        "telegram_id": u.id,
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "language_code": u.language_code,
    }
    try:
        await api.upsert_user(u.id, payload)
    except Exception:
        logger.exception("external API upsert failed for telegram_id=%s", u.id)

    await _send_menu(
        message,
        f"Привіт, {user.first_name or 'атлет'}! Я твій помічник у залі. Чи можу допомогти?",
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await _send_menu(message, "Чим можу допомогти?")


@router.message(F.text == HOME_BUTTON_TEXT)
async def home_button(message: Message) -> None:
    await _send_menu(message, "Чим можу допомогти?")


@router.callback_query(F.data == "action:register")
async def action_register(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поділитися номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Натисни кнопку нижче",
    )
    await callback.message.answer(
        "Для реєстрації поділись, будь ласка, номером телефону.",
        reply_markup=kb,
    )


@router.callback_query(F.data == "action:catalog")
async def action_catalog(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_catalog(callback.message)
    await callback.message.answer("🏠 Головне меню доступне нижче.", reply_markup=_home_kb())


@router.message(F.contact)
async def got_contact(message: Message) -> None:
    if message.contact is None:
        return
    phone = message.contact.phone_number
    tg_id = message.from_user.id if message.from_user else None
    logger.info("Got phone number from telegram_id=%s: %s", tg_id, phone)
    if tg_id is not None:
        async with async_session_factory() as session:
            await set_phone_number(session, telegram_id=tg_id, phone_number=phone)
    await message.answer("Дякую! Номер отримано.", reply_markup=ReplyKeyboardRemove())
    await _send_menu(message, "Чим можу допомогти?")


@router.message(Command("catalog"))
async def cmd_catalog(message: Message) -> None:
    await _send_catalog(message)
    await message.answer("🏠 Головне меню доступне нижче.", reply_markup=_home_kb())


@router.callback_query(F.data.startswith("service:"))
async def choose_service(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    code = callback.data.split("service:", 1)[1]

    services = await list_services_mock()
    chosen = next((s for s in services if s.code == code), None)
    if chosen is None:
        await callback.answer("Послуга не знайдена", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(
        f"Обрано: <b>{chosen.title}</b>\nЦіна: <b>{chosen.price_uah} ₴</b>\n\nЩо робимо далі?"
    )
