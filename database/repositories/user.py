from typing import Optional, List
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import User
from app.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_or_create(self, telegram_id: int, username: str | None = None,
                            first_name: str | None = None, last_name: str | None = None,
                            language_code: str | None = None) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            # Update profile info if provided
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if language_code and user.language_code != language_code:
                user.language_code = language_code
                updated = True
            if updated:
                await self.flush()
            return user

        user = User(
            id=telegram_id,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
        await self.add(user)
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def search(self, query: str, limit: int = 20) -> List[User]:
        stmt = select(User).where(
            or_(
                User.username.ilike(f"%{query}%"),
                User.first_name.ilike(f"%{query}%"),
                User.telegram_id == int(query) if query.isdigit() else False,
            )
        ).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_banned(self, telegram_id: int, banned: bool) -> bool:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.is_banned = banned
            await self.flush()
            return True
        return False

    async def get_all_banned(self, limit: int = 100, offset: int = 0) -> List[User]:
        result = await self.session.execute(
            select(User).where(User.is_banned == True).limit(limit).offset(offset)
        )
        return list(result.scalars().all())