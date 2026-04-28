from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.handlers.start_common import CATALOG_TEXT
from app.handlers.start_menu import send_menu
from app.services.order import create_order
from app.services.service_catalog import get_service_catalog

router = Router(name="start_catalog")

YES_TEXT = "Так"
NO_TEXT = "Ні"

START_TRAINING_TEXT = "Почати тренування"
MENU_TEXT = "🏠 Головне меню"


async def send_catalog(message: Message) -> None:
    services = await get_service_catalog()
    if not services:
        await message.answer("Каталог послуг поки порожній.")
        return
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


@router.callback_query(F.data == "action:catalog")
async def action_catalog(callback: CallbackQuery) -> None:
    await callback.answer()
    await send_catalog(callback.message)


@router.message(Command("catalog"))
async def cmd_catalog(message: Message) -> None:
    await send_catalog(message)


@router.message(F.text == CATALOG_TEXT)
async def catalog_from_menu(message: Message) -> None:
    await send_catalog(message)


@router.callback_query(F.data.startswith("service:"))
async def choose_service(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    code = callback.data.split("service:", 1)[1]

    services = await get_service_catalog()
    if not services:
        await callback.answer("Наразі немає доступних послуг", show_alert=True)
        return

    chosen = next((s for s in services if s.code == code), None)
    if chosen is None:
        await callback.answer("Послуга не знайдена", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(
        f"Обрано: <b>{chosen.title}</b>\nЦіна: <b>{chosen.price_uah} ₴</b>\n\nПерейти до оплати?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=YES_TEXT, callback_data=f"order:confirm:yes:{chosen.code}"),
                    InlineKeyboardButton(text=NO_TEXT, callback_data="order:confirm:no"),
                ]
            ]
        ),
    )

@router.callback_query(F.data == "order:confirm:no")
async def order_confirm_no(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.from_user is None:
        return
    await send_menu(callback.message, "Ок, повертаю в головне меню.", telegram_id=callback.from_user.id)


@router.callback_query(F.data.startswith("order:confirm:yes:"))
async def order_confirm_yes(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.from_user is None or callback.data is None:
        return

    service_id_raw = callback.data.split("order:confirm:yes:", 1)[1]
    try:
        service_id = int(service_id_raw)
    except ValueError:
        await callback.message.answer("Не вдалося створити замовлення: некоректний service_id.")
        return

    order_result = await create_order(telegram_id=callback.from_user.id, service_id=service_id)
    if not order_result.success:
        await callback.message.answer(order_result.message or "Не вдалося створити замовлення.")
        return

    # Mock payment flow for now
    await callback.message.answer("Посилання на оплату: <b>https://pay.example/checkout</b>")
    await callback.message.answer("Оплату отримано. Дякуємо!")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=START_TRAINING_TEXT, callback_data="action:visit"),
                InlineKeyboardButton(text=MENU_TEXT, callback_data="menu:open"),
            ]
        ]
    )
    await callback.message.answer("Що робимо далі?", reply_markup=kb)


@router.callback_query(F.data == "menu:open")
async def menu_open(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.from_user is None:
        return
    await send_menu(callback.message, "Чим можу допомогти?", telegram_id=callback.from_user.id)


@router.callback_query(F.data == "training:start")
async def training_start(callback: CallbackQuery) -> None:
    # Backwards-compatibility: older messages may still contain this callback_data.
    await callback.answer()
    await callback.message.answer("Натисни «Мої послуги», щоб обрати тренування.")

