from __future__ import annotations

from io import BytesIO
from datetime import datetime, time, timedelta, timezone

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
from app.db.session import async_session_factory
from app.db.users_repo import clear_active_visit, clear_active_visit_if_expired, is_active_visit, set_active_visit_until
from app.handlers.start_common import FINISH_WORKOUT_TEXT, MY_WORKOUTS_TEXT, menu_kb
from app.handlers.start_menu import send_menu
from app.services.service_visit import finish_visit, get_service_visit, start_visit
from app.telegram_sensitive import SPOILER_PHOTO_KWARGS, schedule_message_delete

router = Router(name="start_visit")

QR_FINISH_HINT_TEXT = "Натисніть «Завершити тренування», коли закінчите."
WORKOUT_FINISHED_TEXT = "Поверніть ключик та перевіряйте особисті речі"
WORKOUT_ALREADY_CLOSED_TEXT = (
    "Активного тренування немає (можливо, воно вже завершилось автоматично). "
    "Меню відновлено."
)


def _next_midnight_utc() -> datetime:
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
async def visit_from_menu(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    await state.clear()
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


@router.message(F.text == FINISH_WORKOUT_TEXT)
async def finish_training(message: Message) -> None:
    if message.from_user is None:
        return

    telegram_id = message.from_user.id

    async with async_session_factory() as session:
        await clear_active_visit_if_expired(session, telegram_id=telegram_id)
        still_active_locally = await is_active_visit(session, telegram_id=telegram_id)

    # Після півночі локальний прапор уже знятий — користувач «застряг» на старій клавіатурі.
    if not still_active_locally:
        async with async_session_factory() as session:
            await clear_active_visit(session, telegram_id=telegram_id)
        await message.answer(WORKOUT_ALREADY_CLOSED_TEXT)
        await send_menu(message, "Чим можу допомогти?", telegram_id=telegram_id)
        return

    result = await finish_visit(telegram_id)
    if not result.success:
        await message.answer(result.message or "Не вдалося завершити тренування.")
        # Не залишаємо «одну кнопку»: повертаємо повне меню (з finish, якщо візит ще активний).
        await send_menu(message, "Чим можу допомогти?", telegram_id=telegram_id)
        return

    async with async_session_factory() as session:
        await clear_active_visit(session, telegram_id=telegram_id)

    await message.answer(WORKOUT_FINISHED_TEXT)
    await send_menu(message, "Чим можу допомогти?", telegram_id=telegram_id)


@router.callback_query(F.data == "action:finish_visit")
async def finish_training_inline(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.from_user is None or callback.message is None:
        return

    telegram_id = callback.from_user.id

    async with async_session_factory() as session:
        await clear_active_visit_if_expired(session, telegram_id=telegram_id)
        active = await is_active_visit(session, telegram_id=telegram_id)

    if not active:
        async with async_session_factory() as session:
            await clear_active_visit(session, telegram_id=telegram_id)
        await send_menu(callback.message, WORKOUT_ALREADY_CLOSED_TEXT, telegram_id=telegram_id)
        return

    result = await finish_visit(telegram_id)
    if not result.success:
        await callback.message.answer(result.message or "Не вдалося завершити тренування.")
        await send_menu(callback.message, "Чим можу допомогти?", telegram_id=telegram_id)
        return

    async with async_session_factory() as session:
        await clear_active_visit(session, telegram_id=telegram_id)

    await callback.message.answer(WORKOUT_FINISHED_TEXT)
    await send_menu(callback.message, "Чим можу допомогти?", telegram_id=telegram_id)


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

    async with async_session_factory() as session:
        await set_active_visit_until(
            session,
            telegram_id=callback.from_user.id,
            active_until=_next_midnight_utc(),
        )

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

    # Повне меню + «Завершити тренування», а не одна кнопка (щоб не «залипати» після півночі).
    active_menu = menu_kb(is_registered=True, has_active_visit=True)

    qr_message = await callback.message.answer_photo(
        BufferedInputFile(png, filename="visit.png"),
        caption=(
            "Ось твій QR-код для входу. Натисни на зображення, щоб показати код."
            f"{ttl_hint}"
        ),
        reply_markup=active_menu,
        **SPOILER_PHOTO_KWARGS,
    )
    if ttl > 0:
        schedule_message_delete(
            bot=callback.bot,
            chat_id=qr_message.chat.id,
            message_id=qr_message.message_id,
            delay_sec=float(ttl),
        )

    await callback.message.answer(QR_FINISH_HINT_TEXT, reply_markup=active_menu)
