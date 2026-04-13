from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    r = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return r.scalar_one_or_none()


async def register_or_update(
    session: AsyncSession,
    *,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
) -> User:
    user = await get_by_telegram_id(session, telegram_id)
    if user is None:
        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        session.add(user)
    else:
        user.username = username
        user.first_name = first_name
    await session.commit()
    await session.refresh(user)
    return user


async def set_phone_number(session: AsyncSession, *, telegram_id: int, phone_number: str) -> User:
    user = await get_by_telegram_id(session, telegram_id)
    if user is None:
        user = User(telegram_id=telegram_id, phone_number=phone_number)
        session.add(user)
    else:
        user.phone_number = phone_number
    await session.commit()
    await session.refresh(user)
    return user
