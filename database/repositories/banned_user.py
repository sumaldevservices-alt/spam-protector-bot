from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import BannedUser
from app.database.repositories.base import BaseRepository


class BannedUserRepository(BaseRepository[BannedUser]):
    def __init__(self, session: AsyncSession):
        super().__init__(BannedUser, session)

    async def is_banned(self, telegram_id: int) -> bool:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(BannedUser).where(
                and_(
                    BannedUser.telegram_id == telegram_id,
                    BannedUser.is_active == True,
                    (BannedUser.is_permanent == True) | (BannedUser.expires_at > now)
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def ban(self, telegram_id: int, username: str | None, reason: str | None,
                  banned_by: int, is_permanent: bool = True,
                  expires_at: datetime | None = None) -> BannedUser:
        existing = await self.session.execute(
            select(BannedUser).where(BannedUser.telegram_id == telegram_id)
        )
        banned = existing.scalar_one_or_none()
        if banned:
            banned.is_active = True
            banned.reason = reason
            banned.banned_by = banned_by
            banned.is_permanent = is_permanent
            banned.expires_at = expires_at
            banned.username = username
        else:
            banned = BannedUser(
                telegram_id=telegram_id,
                username=username,
                reason=reason,
                banned_by=banned_by,
                is_permanent=is_permanent,
                expires_at=expires_at,
                is_active=True,
            )
            await self.add(banned)
        return banned

    async def unban(self, telegram_id: int) -> bool:
        banned = await self.session.execute(
            select(BannedUser).where(BannedUser.telegram_id == telegram_id)
        )
        banned = banned.scalar_one_or_none()
        if banned:
            banned.is_active = False
            await self.flush()
            return True
        return False

    async def get_active_bans(self, limit: int = 100, offset: int = 0):
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(BannedUser).where(
                and_(
                    BannedUser.is_active == True,
                    (BannedUser.is_permanent == True) | (BannedUser.expires_at > now)
                )
            ).limit(limit).offset(offset)
        )
        return list(result.scalars().all())