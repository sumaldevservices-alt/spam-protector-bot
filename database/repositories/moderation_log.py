from typing import Optional, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import ModerationLog, ModerationAction
from app.database.repositories.base import BaseRepository


class ModerationLogRepository(BaseRepository[ModerationLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(ModerationLog, session)

    async def add_log(self, channel_id: int, message_id: int, action: ModerationAction,
                      user_id: int | None = None, reason: str | None = None,
                      content_preview: str | None = None, metadata: dict | None = None,
                      deleted_by_bot: bool = True) -> ModerationLog:
        from datetime import datetime, timezone
        log = ModerationLog(
            channel_id=channel_id,
            message_id=message_id,
            user_id=user_id,
            action=action,
            reason=reason,
            content_preview=content_preview,
            metadata=metadata or {},
            deleted_by_bot=deleted_by_bot,
            timestamp=datetime.now(timezone.utc),
        )
        await self.add(log)
        return log

    async def get_channel_logs(self, channel_id: int, limit: int = 50, offset: int = 0) -> List[ModerationLog]:
        result = await self.session.execute(
            select(ModerationLog).where(ModerationLog.channel_id == channel_id)
            .order_by(ModerationLog.timestamp.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def get_channel_logs_count(self, channel_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(ModerationLog).where(ModerationLog.channel_id == channel_id)
        )
        return result.scalar_one()