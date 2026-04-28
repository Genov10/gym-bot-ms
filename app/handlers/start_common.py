from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

HOME_BUTTON_TEXT = "🏠 Головне меню"

SEX_MALE_TEXT = "Чоловік"
SEX_FEMALE_TEXT = "Жінка"

START_TEXT = "Почати"
CATALOG_TEXT = "Каталог"
MY_WORKOUTS_TEXT = "Мої тренування"
FINISH_WORKOUT_TEXT = "Завершити тренування"


def menu_kb(*, is_registered: bool, has_active_visit: bool) -> ReplyKeyboardMarkup:
    if not is_registered:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=START_TEXT)]],
            resize_keyboard=True,
            one_time_keyboard=False,
            input_field_placeholder="Натисни «Почати»",
        )

    row = [KeyboardButton(text=CATALOG_TEXT), KeyboardButton(text=MY_WORKOUTS_TEXT)]
    if has_active_visit:
        row.append(KeyboardButton(text=FINISH_WORKOUT_TEXT))

    return ReplyKeyboardMarkup(
        keyboard=[row],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Обери дію",
    )


def home_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=HOME_BUTTON_TEXT)]],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Обери дію",
    )

