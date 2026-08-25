from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import ChannelSettings, LinkSensitivity
from app.database.repositories.base import BaseRepository


class ChannelSettingsRepository(BaseRepository[ChannelSettings]):
    def __init__(self, session: AsyncSession):
        super().__init__(ChannelSettings, session)

    async def get_or_create(self, channel_id: int) -> ChannelSettings:
        result = await self.session.execute(
            select(ChannelSettings).where(ChannelSettings.channel_id == channel_id)
        )
        settings = result.scalar_one_or_none()
        if settings:
            return settings

        settings = ChannelSettings(channel_id=channel_id)
        await self.add(settings)
        return settings

    async def get_by_channel(self, channel_id: int) -> Optional[ChannelSettings]:
        result = await self.session.execute(
            select(ChannelSettings).where(ChannelSettings.channel_id == channel_id)
        )
        return result.scalar_one_or_none()