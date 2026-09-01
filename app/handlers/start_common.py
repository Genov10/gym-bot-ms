from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

HOME_BUTTON_TEXT = "🏠 Головне меню"

ADMIN_CONTACT_TEXT = "Адміністратор"
ADMIN_TELEGRAM_USERNAME = "alin_kozachenko"
ADMIN_TELEGRAM_URL = f"https://t.me/{ADMIN_TELEGRAM_USERNAME}"

SEX_MALE_TEXT = "Чоловік"
SEX_FEMALE_TEXT = "Жінка"

START_TEXT = "Почати"
CATALOG_TEXT = "Каталог"
MY_WORKOUTS_TEXT = "Мої тренування"

# Reply-кнопки головного меню — не обробляти їх як кроки реєстрації (FSM).
MENU_BUTTON_TEXTS: frozenset[str] = frozenset(
    {
        START_TEXT,
        CATALOG_TEXT,
        MY_WORKOUTS_TEXT,
        HOME_BUTTON_TEXT,
        ADMIN_CONTACT_TEXT,
    }
)


def admin_contact_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Написати @{ADMIN_TELEGRAM_USERNAME}",
                    url=ADMIN_TELEGRAM_URL,
                )
            ]
        ]
    )


def menu_kb(*, is_registered: bool) -> ReplyKeyboardMarkup:
    admin_row = [KeyboardButton(text=ADMIN_CONTACT_TEXT)]

    if not is_registered:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=START_TEXT)], admin_row],
            resize_keyboard=True,
            one_time_keyboard=False,
            input_field_placeholder="Натисни «Почати»",
        )

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=CATALOG_TEXT),
                KeyboardButton(text=MY_WORKOUTS_TEXT),
                KeyboardButton(text=ADMIN_CONTACT_TEXT),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Обери дію",
    )


def home_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=HOME_BUTTON_TEXT)],
            [KeyboardButton(text=ADMIN_CONTACT_TEXT)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Обери дію",
    )

