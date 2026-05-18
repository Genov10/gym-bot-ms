from __future__ import annotations

import logging
import re
from datetime import date, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from app.db.session import async_session_factory
from app.db.users_repo import mark_user_verified, set_phone_number
from app.handlers.start_common import MENU_BUTTON_TEXTS, SEX_FEMALE_TEXT, SEX_MALE_TEXT, START_TEXT
from app.handlers.start_menu import send_menu
from app.services.customer import register_customer

logger = logging.getLogger(__name__)
router = Router(name="start_registration")

SKIP_EMAIL_TEXT = "Не вказувати"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", re.IGNORECASE)

REGISTRATION_SUCCESS_TEXT = (
    "Дякую! Реєстрація завершена.\n\n"
    "Тепер ви можете користуватися ботом.\n\n"
    "У каталозі ви можете побачити доступні послуги та обрати потрібну вам.\n\n"
    "У списку «Мої тренування» — активні абонементи та старт тренування."
)


def _is_valid_name_part(part: str) -> bool:
    if len(part) < 2:
        return False
    for char in part:
        if char in "-'ʼ":
            continue
        if not char.isalpha():
            return False
    return True


class RegisterFlow(StatesGroup):
    contact = State()
    full_name = State()
    sex = State()
    birth_date = State()
    email = State()


def _parse_full_name(raw: str) -> tuple[str, str] | None:
    parts = [p for p in raw.split() if p]
    if len(parts) < 2:
        return None
    first_name, *rest = parts
    last_name = " ".join(rest)
    if not _is_valid_name_part(first_name) or not _is_valid_name_part(last_name):
        return None
    return first_name, last_name


def _validate_email(raw: str) -> str | None:
    email = raw.strip()
    if not email or not _EMAIL_RE.fullmatch(email):
        return None
    return email


async def _finish_registration(message: Message, state: FSMContext, *, email: str | None) -> None:
    if message.from_user is None:
        return

    data = await state.get_data()
    phone = data.get("phone")
    first_name = data.get("first_name") or data.get("name")
    lastname = data.get("lastname") or data.get("last_name")
    if not phone or not first_name or not lastname:
        await message.answer("Не вдалося завершити реєстрацію. Спробуйте ще раз з «Почати».")
        await state.clear()
        return

    result = await register_customer(
        message.from_user.id,
        first_name=first_name,
        lastname=lastname,
        phone=phone,
        username=message.from_user.username,
        sex=data.get("sex"),
        email=email,
        birth_date=data.get("birth_date"),
    )

    if result.success or result.already_exists:
        async with async_session_factory() as session:
            await mark_user_verified(
                session,
                telegram_id=message.from_user.id,
                phone_number=phone,
                first_name=first_name,
            )
        await state.clear()
        menu_text = REGISTRATION_SUCCESS_TEXT
        if result.already_exists:
            menu_text = f"{result.message or 'Ви вже зареєстровані.'}\n\n{REGISTRATION_SUCCESS_TEXT}"
        await send_menu(
            message,
            menu_text,
            telegram_id=message.from_user.id,
            is_registered=True,
        )
        return

    await state.clear()
    await message.answer(result.message or "Не вдалося завершити реєстрацію. Спробуйте пізніше.")
    await send_menu(message, "Спробуйте реєстрацію ще раз через «Почати».", telegram_id=message.from_user.id)


async def _begin_register(message: Message, state: FSMContext) -> None:
    await state.clear()
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поділитися номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Натисни кнопку нижче",
    )
    await message.answer("Для реєстрації поділіться, будь ласка, номером телефону.", reply_markup=kb)
    await state.set_state(RegisterFlow.contact)


@router.message(F.text == START_TEXT)
async def action_register_from_menu(message: Message, state: FSMContext) -> None:
    await _begin_register(message, state)


@router.callback_query(F.data == "action:register")
async def action_register(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _begin_register(callback.message, state)


@router.message(RegisterFlow.contact, F.contact)
async def register_got_contact(message: Message, state: FSMContext) -> None:
    if message.contact is None or message.from_user is None:
        return

    if message.contact.user_id is not None and message.contact.user_id != message.from_user.id:
        await message.answer("Поділіться своїм номером через кнопку нижче, а не контактом іншої людини.")
        return

    phone = message.contact.phone_number
    logger.info("Got phone number from telegram_id=%s: %s", message.from_user.id, phone)

    async with async_session_factory() as session:
        await set_phone_number(session, telegram_id=message.from_user.id, phone_number=phone)

    await state.update_data(phone=phone)
    await message.answer(
        "Введіть <b>ім'я та прізвище</b> через пробіл.\n"
        "Спочатку ім'я, потім прізвище — наприклад: <b>Олена Коваленко</b>",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(RegisterFlow.full_name)


@router.message(RegisterFlow.contact)
async def register_got_contact_invalid(message: Message) -> None:
    await message.answer("Натисніть кнопку «📱 Поділитися номером» нижче")


@router.message(RegisterFlow.full_name, F.text, ~F.text.in_(MENU_BUTTON_TEXTS))
async def register_got_full_name(message: Message, state: FSMContext) -> None:
    parsed = _parse_full_name((message.text or "").strip())
    if parsed is None:
        await message.answer(
            "Невірний формат. Введіть ім'я та прізвище, "
            "наприклад: <b>Олена Коваленко</b> "
        )
        return

    first_name, lastname = parsed
    await state.update_data(first_name=first_name, lastname=lastname)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=SEX_MALE_TEXT), KeyboardButton(text=SEX_FEMALE_TEXT)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Обери варіант",
    )
    await message.answer("Оберіть, будь ласка, свою стать", reply_markup=kb)
    await state.set_state(RegisterFlow.sex)


@router.message(RegisterFlow.full_name)
async def register_got_full_name_invalid(message: Message) -> None:
    await message.answer("Введіть ім'я та прізвище текстом, наприклад: <b>Іван Петренко</b>.")


@router.message(RegisterFlow.sex, F.text.in_({SEX_MALE_TEXT, SEX_FEMALE_TEXT}))
async def register_got_sex(message: Message, state: FSMContext) -> None:
    sex = "male" if message.text == SEX_MALE_TEXT else "female"
    await state.update_data(sex=sex)
    await message.answer(
        "Введіть, будь ласка, дату народження у форматі <b>01.01.2000</b>.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(RegisterFlow.birth_date)


@router.message(RegisterFlow.sex)
async def register_got_sex_invalid(message: Message) -> None:
    await message.answer(f"Будь ласка, оберіть стать: {SEX_MALE_TEXT} або {SEX_FEMALE_TEXT}.")


@router.message(RegisterFlow.birth_date, F.text, ~F.text.in_(MENU_BUTTON_TEXTS))
async def register_got_birth_date(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    try:
        birth_date = datetime.strptime(raw, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("Невірний формат. Введіть дату як <b>01.01.2000</b>.")
        return

    today = date.today()
    if birth_date > today:
        await message.answer("Дата народження не може бути в майбутньому.")
        return
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    if age > 120:
        await message.answer("Перевірте дату народження — вік має бути до 120 років.")
        return

    await state.update_data(birth_date=birth_date)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=SKIP_EMAIL_TEXT)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="example@email.com",
    )
    await message.answer("Введіть пошту", reply_markup=kb)
    await state.set_state(RegisterFlow.email)


@router.message(RegisterFlow.email, F.text == SKIP_EMAIL_TEXT)
async def register_skip_email(message: Message, state: FSMContext) -> None:
    await _finish_registration(message, state, email=None)


@router.message(RegisterFlow.email, F.text, ~F.text.in_(MENU_BUTTON_TEXTS))
async def register_got_email(message: Message, state: FSMContext) -> None:
    email = _validate_email(message.text or "")
    if email is None:
        await message.answer(
            "Невірний формат пошти. Введіть, наприклад: <b>name@example.com</b> "
            f"або натисніть «{SKIP_EMAIL_TEXT}»."
        )
        return

    await _finish_registration(message, state, email=email)


@router.message(RegisterFlow.email)
async def register_got_email_invalid(message: Message) -> None:
    await message.answer(f"Введіть пошту або натисніть «{SKIP_EMAIL_TEXT}».")
