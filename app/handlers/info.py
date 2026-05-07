from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="info")

INFO_TEXT = """Я твій бот-помічник у тренуваннях в Gym17!

Тут ти можеш переглянути послуги, керувати тренуваннями та отримати потрібну інформацію!

Звʼязок з адміністратором: @genov01"
"""


@router.message(Command("info"))
async def cmd_info(message: Message) -> None:
    await message.answer(INFO_TEXT)
