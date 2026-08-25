from typing import Optional, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Channel, ChannelStatus
from app.database.repositories.base import BaseRepository


class ChannelRepository(BaseRepository[Channel]):
    def __init__(self, session: AsyncSession):
        super().__init__(Channel, session)

    async def create(self, telegram_chat_id: int, title: str, owner_user_id: int,
                     username: str | None = None, invite_link: str | None = None) -> Channel:
        channel = Channel(
            id=telegram_chat_id,
            telegram_chat_id=telegram_chat_id,
            title=title,
            username=username,
            owner_user_id=owner_user_id,
            invite_link=invite_link,
            status=ChannelStatus.PENDING,
        )
        await self.add(channel)
        return channel

    async def get_by_chat_id(self, telegram_chat_id: int) -> Optional[Channel]:
        result = await self.session.execute(
            select(Channel).where(Channel.telegram_chat_id == telegram_chat_id)
        )
        return result.scalar_one_or_none()

    async def get_user_channels(self, owner_user_id: int, active_only: bool = False) -> List[Channel]:
        stmt = select(Channel).where(Channel.owner_user_id == owner_user_id)
        if active_only:
            stmt = stmt.where(Channel.status == ChannelStatus.ACTIVE)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_status(self, telegram_chat_id: int, status: ChannelStatus) -> bool:
        channel = await self.get_by_chat_id(telegram_chat_id)
        if channel:
            channel.status = status
            await self.flush()
            return True
        return False

    async def update_admin_perms(self, telegram_chat_id: int, bot_is_admin: bool,
                                  can_delete_messages: bool) -> bool:
        channel = await self.get_by_chat_id(telegram_chat_id)
        if channel:
            channel.bot_is_admin = bot_is_admin
            channel.can_delete_messages = can_delete_messages
            await self.flush()
            return True
        return False

    async def update_invite_link(self, telegram_chat_id: int, invite_link: str) -> bool:
        channel = await self.get_by_chat_id(telegram_chat_id)
        if channel:
            channel.invite_link = invite_link
            await self.flush()
            return True
        return False

    async def get_active_channels_count_for_user(self, owner_user_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Channel).where(
                and_(Channel.owner_user_id == owner_user_id, Channel.status == ChannelStatus.ACTIVE)
            )
        )
        return result.scalar_one()

    async def get_all_active(self, limit: int = 100, offset: int = 0) -> List[Channel]:
        result = await self.session.execute(
            select(Channel).where(Channel.status == ChannelStatus.ACTIVE).limit(limit).offset(offset)
        )
        return list(result.scalars().all())