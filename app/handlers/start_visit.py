from __future__ import annotations

from io import BytesIO

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import segno

from app.config import settings
from app.handlers.start_common import MY_WORKOUTS_TEXT, menu_kb
from app.services.service_visit import get_service_visit, start_visit
from app.telegram_sensitive import SPOILER_PHOTO_KWARGS, schedule_message_delete

router = Router(name="start_visit")


@router.callback_query(F.data == "action:visit")
async def action_visit(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.from_user is None:
        return
    await send_customer_catalog(callback.message, telegram_id=callback.from_user.id)


@router.message(F.text == MY_WORKOUTS_TEXT)
async def visit_from_menu(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    await state.clear()
    await send_customer_catalog(message, telegram_id=message.from_user.id)


async def send_customer_catalog(message: Message, *, telegram_id: int | None = None) -> None:
    if telegram_id is None:
        if message.from_user is None:
            return
        telegram_id = message.from_user.id

    services = await get_service_visit(telegram_id)
    if not services:
        await message.answer("У Вас поки немає доступних послуг, саме час оновити абонемент)")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=s.name,
                    callback_data=f"customer_service:{s.id}",
                )
            ]
            for s in services
        ]
    )
    await message.answer("Доступні тренування", reply_markup=kb)


@router.callback_query(F.data.startswith("customer_service:"))
async def customer_service_chosen(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    service_id = int(callback.data.split("customer_service:", 1)[1])
    await callback.answer()
    if callback.from_user is None or callback.message is None:
        return

    result = await start_visit(telegram_id=callback.from_user.id, service_id=service_id)
    if not result.success or not result.visit:
        await callback.message.answer(result.message or "Не вдалося розпочати візит.")
        return

    qr = segno.make(result.visit)
    buf = BytesIO()
    qr.save(buf, kind="png", scale=8, border=2)
    png = buf.getvalue()

    ttl = settings.qr_message_ttl_sec
    ttl_hint = ""
    if ttl >= 60:
        ttl_hint = f" Фото зникне з чату через {ttl // 60} хв."
    elif ttl > 0:
        ttl_hint = f" Фото зникне через {ttl} с."

    menu = menu_kb(is_registered=True)

    qr_message = await callback.message.answer_photo(
        BufferedInputFile(png, filename="visit.png"),
        caption=(
            "Ось твій QR-код для входу. Натисни на зображення, щоб показати код."
            f"{ttl_hint}"
        ),
        reply_markup=menu,
        **SPOILER_PHOTO_KWARGS,
    )
    if ttl > 0:
        schedule_message_delete(
            bot=callback.bot,
            chat_id=qr_message.chat.id,
            message_id=qr_message.message_id,
            delay_sec=float(ttl),
        )
