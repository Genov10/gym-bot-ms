from __future__ import annotations

from io import BytesIO
from datetime import datetime, time, timedelta, timezone

from aiogram import F, Router
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

import segno

from app.db.session import async_session_factory
from app.db.users_repo import clear_active_visit, clear_active_visit_if_expired, is_active_visit, set_active_visit_until
from app.handlers.start_menu import send_menu
from app.handlers.start_common import FINISH_WORKOUT_TEXT, MY_WORKOUTS_TEXT
from app.services.service_visit import finish_visit, get_service_visit, start_visit

router = Router(name="start_visit")

FINISH_VISIT_TEXT = "Завершити тренування"


def _finish_visit_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=FINISH_VISIT_TEXT)]],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Коли закінчиш — натисни кнопку нижче",
    )


def _next_midnight_utc() -> datetime:
    # Expire at the next local midnight, stored in UTC
    local_now = datetime.now().astimezone()
    next_day = (local_now + timedelta(days=1)).date()
    local_midnight = datetime.combine(next_day, time.min, tzinfo=local_now.tzinfo)
    return local_midnight.astimezone(timezone.utc)


@router.callback_query(F.data == "action:visit")
async def action_visit(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.from_user is None:
        return
    async with async_session_factory() as session:
        await clear_active_visit_if_expired(session, telegram_id=callback.from_user.id)
    await send_customer_catalog(callback.message, telegram_id=callback.from_user.id)


@router.message(F.text == MY_WORKOUTS_TEXT)
async def visit_from_menu(message: Message) -> None:
    if message.from_user is None:
        return
    async with async_session_factory() as session:
        await clear_active_visit_if_expired(session, telegram_id=message.from_user.id)
    await send_customer_catalog(message, telegram_id=message.from_user.id)


async def send_customer_catalog(message: Message, *, telegram_id: int | None = None) -> None:
    if telegram_id is None:
        if message.from_user is None:
            return
        telegram_id = message.from_user.id

    services = await get_service_visit(telegram_id)
    if not services:
        await message.answer("У Вас поки немає доступних послуг, саме час оновити абонемен)")
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


@router.message(F.text == FINISH_VISIT_TEXT)
async def finish_training(message: Message) -> None:
    if message.from_user is None:
        return

    async with async_session_factory() as session:
        await clear_active_visit_if_expired(session, telegram_id=message.from_user.id)

    result = await finish_visit(message.from_user.id)
    if not result.success:
        await message.answer(result.message or "Не вдалося завершити тренування.")
        return

    async with async_session_factory() as session:
        await clear_active_visit(session, telegram_id=message.from_user.id)

    await message.answer("Тренування завершено. До зустрічі!", reply_markup=ReplyKeyboardRemove())
    await send_menu(message, "", telegram_id=message.from_user.id)


@router.message(F.text == FINISH_WORKOUT_TEXT)
async def finish_training_from_menu(message: Message) -> None:
    # alias for menu button text (same as FINISH_VISIT_TEXT)
    await finish_training(message)


@router.callback_query(F.data == "action:finish_visit")
async def finish_training_inline(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.from_user is None:
        return

    async with async_session_factory() as session:
        await clear_active_visit_if_expired(session, telegram_id=callback.from_user.id)
        active = await is_active_visit(session, telegram_id=callback.from_user.id)

    if not active:
        await send_menu(callback.message, "Активного тренування немає.", telegram_id=callback.from_user.id)
        return

    result = await finish_visit(callback.from_user.id)
    if not result.success:
        await callback.message.answer(result.message or "Не вдалося завершити тренування.")
        return

    async with async_session_factory() as session:
        await clear_active_visit(session, telegram_id=callback.from_user.id)

    await callback.message.answer("Тренування завершено. До зустрічі!")
    await send_menu(callback.message, "", telegram_id=callback.from_user.id)


@router.callback_query(F.data.startswith("customer_service:"))
async def customer_service_chosen(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    service_id = int(callback.data.split("customer_service:", 1)[1])
    await callback.answer()
    if callback.from_user is None:
        return

    result = await start_visit(telegram_id=callback.from_user.id, service_id=service_id)
    if not result.success or not result.visit:
        await callback.message.answer(result.message or "Не вдалося розпочати візит.")
        return

    async with async_session_factory() as session:
        await set_active_visit_until(session, telegram_id=callback.from_user.id, active_until=_next_midnight_utc())

    qr = segno.make(result.visit)
    buf = BytesIO()
    qr.save(buf, kind="png", scale=8, border=2)
    png = buf.getvalue()

    await callback.message.answer_photo(
        BufferedInputFile(png, filename="visit.png"),
        caption="Ось твій QR-код для входу.",
        reply_markup=_finish_visit_kb(),
    )

