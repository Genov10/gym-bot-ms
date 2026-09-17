from __future__ import annotations

import html
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
from app.services.service_visit import (
    CustomerGymServiceInfo,
    confirm_freeze,
    get_customer_gym_service_info,
    get_freeze_preview,
    get_service_visit,
    start_visit,
)
from app.telegram_sensitive import SPOILER_PHOTO_KWARGS, schedule_message_delete

router = Router(name="start_visit")

START_TRAINING_BUTTON_TEXT = "Отримати QR-код та почати тренування"
FREEZE_BUTTON_TEXT = "Заморозити абонемент"
FREEZE_CONFIRM_BUTTON_TEXT = "Так, я хочу його заморозити"


def _format_service_info_message(info: CustomerGymServiceInfo) -> str:
    lines = [f"<b>{html.escape(info.service_name)}</b>"]

    if info.description:
        lines.append(html.escape(info.description))

    if info.date_from:
        lines.append(f"Початок абонемента: {html.escape(info.date_from)}")

    if info.date_to:
        lines.append(f"Кінець абонемента: {html.escape(info.date_to)}")

    if info.lefted_visits_amount is not None:
        lines.append(f"Залишилось відвідувань: {info.lefted_visits_amount}")

    return "\n".join(lines)


async def _send_visit_qr(message: Message, *, telegram_id: int, service_id: int) -> None:
    result = await start_visit(telegram_id=telegram_id, service_id=service_id)
    if not result.success or not result.visit:
        await message.answer(result.message or "Не вдалося розпочати візит.")
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

    qr_message = await message.answer_photo(
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
            bot=message.bot,
            chat_id=qr_message.chat.id,
            message_id=qr_message.message_id,
            delay_sec=float(ttl),
        )


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
    await message.answer("Список ваших абонементів:\n", reply_markup=kb)


@router.callback_query(F.data.startswith("customer_service:"))
async def customer_service_chosen(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    service_id = int(callback.data.split("customer_service:", 1)[1])
    await callback.answer()
    if callback.from_user is None or callback.message is None:
        return

    info = await get_customer_gym_service_info(
        telegram_id=callback.from_user.id,
        service_id=service_id,
    )
    if info is None:
        await callback.message.answer("Не вдалося отримати інформацію про абонемент.")
        return

    rows = [
        [
            InlineKeyboardButton(
                text=START_TRAINING_BUTTON_TEXT,
                callback_data=f"start_training:{service_id}",
            )
        ]
    ]
    if info.can_be_frosen:
        rows.append(
            [
                InlineKeyboardButton(
                    text=FREEZE_BUTTON_TEXT,
                    callback_data=f"freeze_preview:{service_id}",
                )
            ]
        )

    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.answer(_format_service_info_message(info), reply_markup=kb)


@router.callback_query(F.data.startswith("start_training:"))
async def start_training_chosen(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    service_id = int(callback.data.split("start_training:", 1)[1])
    await callback.answer()
    if callback.from_user is None or callback.message is None:
        return

    await _send_visit_qr(
        callback.message,
        telegram_id=callback.from_user.id,
        service_id=service_id,
    )


@router.callback_query(F.data.startswith("freeze_preview:"))
async def freeze_preview_chosen(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    service_id = int(callback.data.split("freeze_preview:", 1)[1])
    await callback.answer()
    if callback.from_user is None or callback.message is None:
        return

    preview = await get_freeze_preview(
        telegram_id=callback.from_user.id,
        service_id=service_id,
    )
    if preview is None:
        await callback.message.answer("Не вдалося отримати умови заморозки.")
        return

    if not preview.can_be_frosen:
        await callback.message.answer("Цей абонемент зараз неможливо заморозити.")
        return

    lines = [f"<b>{html.escape(preview.service_name)}</b>", ""]
    for rule in preview.rules:
        lines.append(html.escape(rule))
    lines.extend(["", "Ви впевнені, що хочете заморозити абонемент?"])

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=FREEZE_CONFIRM_BUTTON_TEXT,
                    callback_data=f"freeze_confirm:{service_id}",
                )
            ]
        ]
    )
    await callback.message.answer("\n".join(lines), reply_markup=kb)


@router.callback_query(F.data.startswith("freeze_confirm:"))
async def freeze_confirm_chosen(callback: CallbackQuery) -> None:
    if callback.data is None:
        return
    service_id = int(callback.data.split("freeze_confirm:", 1)[1])
    await callback.answer()
    if callback.from_user is None or callback.message is None:
        return

    telegram_id = callback.from_user.id
    result = await confirm_freeze(telegram_id=telegram_id, service_id=service_id)
    if not result.success:
        await callback.message.answer(result.message or "Не вдалося заморозити абонемент.")
        return

    info = await get_customer_gym_service_info(telegram_id=telegram_id, service_id=service_id)
    name = info.service_name if info is not None else "Абонемент"
    await callback.message.answer(f"<b>{html.escape(name)}</b> успішно заморожено")
