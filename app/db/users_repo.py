from datetime import datetime, timezone

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


async def set_active_visit_until(session: AsyncSession, *, telegram_id: int, active_until: datetime) -> User:
    user = await get_by_telegram_id(session, telegram_id)
    if user is None:
        user = User(telegram_id=telegram_id, active_visit_until=active_until)
        session.add(user)
    else:
        user.active_visit_until = active_until
    await session.commit()
    await session.refresh(user)
    return user


async def clear_active_visit(session: AsyncSession, *, telegram_id: int) -> None:
    user = await get_by_telegram_id(session, telegram_id)
    if user is None:
        return
    user.active_visit_until = None
    await session.commit()


async def is_active_visit(session: AsyncSession, *, telegram_id: int) -> bool:
    user = await get_by_telegram_id(session, telegram_id)
    if user is None or user.active_visit_until is None:
        return False
    now = datetime.now(timezone.utc)
    return user.active_visit_until > now


async def clear_active_visit_if_expired(session: AsyncSession, *, telegram_id: int) -> None:
    user = await get_by_telegram_id(session, telegram_id)
    if user is None or user.active_visit_until is None:
        return
    now = datetime.now(timezone.utc)
    if user.active_visit_until <= now:
        user.active_visit_until = None
        await session.commit()
