from __future__ import annotations

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from app.db.session import async_session_factory
from app.db.users_repo import set_phone_number
from app.handlers.start_common import SEX_FEMALE_TEXT, SEX_MALE_TEXT, START_TEXT
from app.handlers.start_menu import send_menu
from app.services.customer import register_customer

logger = logging.getLogger(__name__)
router = Router(name="start_registration")


class RegisterFlow(StatesGroup):
    sex = State()
    birth_date = State()
    contact = State()


async def _begin_register(message: Message, state: FSMContext) -> None:
    await state.clear()
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=SEX_MALE_TEXT), KeyboardButton(text=SEX_FEMALE_TEXT)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Обери варіант",
    )
    await message.answer("Для реєстрації обери, будь ласка, свою стать.", reply_markup=kb)
    await state.set_state(RegisterFlow.sex)


@router.message(F.text == START_TEXT)
async def action_register_from_menu(message: Message, state: FSMContext) -> None:
    await _begin_register(message, state)


# Backwards-compatibility: older inline menu messages might still exist
@router.callback_query(F.data == "action:register")
async def action_register(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _begin_register(callback.message, state)


@router.message(RegisterFlow.sex, F.text.in_({SEX_MALE_TEXT, SEX_FEMALE_TEXT}))
async def register_got_sex(message: Message, state: FSMContext) -> None:
    sex = "male" if message.text == SEX_MALE_TEXT else "female"
    await state.update_data(sex=sex)
    await message.answer(
        "Введи, будь ласка, дату народження у форматі <b>19.04.2005</b>.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(RegisterFlow.birth_date)


@router.message(RegisterFlow.sex)
async def register_got_sex_invalid(message: Message) -> None:
    await message.answer(f"Будь ласка, обери одну з кнопок: {SEX_MALE_TEXT} або {SEX_FEMALE_TEXT}.")


@router.message(RegisterFlow.birth_date, F.text)
async def register_got_birth_date(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    try:
        birth_date = datetime.strptime(raw, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("Невірний формат. Введи дату як <b>19.04.2005</b>.")
        return

    await state.update_data(birth_date=birth_date)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поділитися номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Натисни кнопку нижче",
    )
    await message.answer("Тепер поділись, будь ласка, номером телефону.", reply_markup=kb)
    await state.set_state(RegisterFlow.contact)


@router.message(RegisterFlow.contact, F.contact)
async def got_contact(message: Message, state: FSMContext) -> None:
    if message.contact is None:
        return
    phone = message.contact.phone_number
    tg_id = message.from_user.id if message.from_user else None
    logger.info("Got phone number from telegram_id=%s: %s", tg_id, phone)
    if tg_id is not None:
        async with async_session_factory() as session:
            await set_phone_number(session, telegram_id=tg_id, phone_number=phone)

    await message.answer("Дякую! Номер отримано.", reply_markup=ReplyKeyboardRemove())

    if message.from_user is not None:
        data = await state.get_data()
        result = await register_customer(
            telegram_id=message.from_user.id,
            name=message.from_user.username or message.from_user.first_name or "",
            phone=phone,
            sex=data.get("sex"),
            email=None,
            birth_date=data.get("birth_date"),
        )
        if not result.success:
            await message.answer(result.message or "Цей номер телефону вже зареєстрований.")

    await state.clear()
    await send_menu(message, "Чим можу допомогти?", telegram_id=message.from_user.id if message.from_user else None)

