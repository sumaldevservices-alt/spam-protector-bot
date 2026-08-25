from typing import Optional, List
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Subscription, SubscriptionStatus, ChannelStatus
from app.database.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self, session: AsyncSession):
        super().__init__(Subscription, session)

    async def get_active_for_user(self, user_id: int) -> List[Subscription]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Subscription).where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at > now
                )
            )
        )
        return list(result.scalars().all())

    async def get_by_channel(self, channel_id: int) -> Optional[Subscription]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Subscription).where(
                and_(
                    Subscription.channel_id == channel_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at > now
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_user_subscriptions(self, user_id: int) -> List[Subscription]:
        result = await self.session.execute(
            select(Subscription).where(Subscription.user_id == user_id).order_by(Subscription.started_at.desc())
        )
        return list(result.scalars().all())

    async def count_active_channels_for_user(self, user_id: int) -> int:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(func.count()).select_from(Subscription).where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at > now
                )
            )
        )
        return result.scalar_one()

    async def create(self, user_id: int, plan_id: int, channel_id: int | None,
                     status: SubscriptionStatus, started_at: datetime, expires_at: datetime,
                     channel_limit: int, auto_renew: bool = False) -> Subscription:
        sub = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            channel_id=channel_id,
            status=status,
            started_at=started_at,
            expires_at=expires_at,
            channel_limit=channel_limit,
            auto_renew=auto_renew,
        )
        await self.add(sub)
        return sub

    async def extend(self, subscription_id: int, days: int) -> Optional[Subscription]:
        sub = await self.get(subscription_id)
        if sub:
            sub.expires_at = sub.expires_at.replace(tzinfo=timezone.utc) + timedelta(days=days)
            if sub.status == SubscriptionStatus.EXPIRED:
                sub.status = SubscriptionStatus.ACTIVE
            await self.flush()
            return sub
        return None

    async def cancel(self, subscription_id: int) -> bool:
        sub = await self.get(subscription_id)
        if sub:
            sub.status = SubscriptionStatus.CANCELLED
            await self.flush()
            return True
        return False

    async def expire_overdue(self) -> int:
        """Expire overdue subscriptions and return count."""
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Subscription).where(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at <= now
                )
            )
        )
        subs = list(result.scalars().all())
        for sub in subs:
            sub.status = SubscriptionStatus.EXPIRED
        if subs:
            await self.flush()
        return len(subs)

    async def get_expired_for_user(self, user_id: int) -> List[Subscription]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Subscription).where(
                and_(
                    Subscription.user_id == user_id,
                    or_(
                        Subscription.status == SubscriptionStatus.EXPIRED,
                        and_(
                            Subscription.status == SubscriptionStatus.ACTIVE,
                            Subscription.expires_at <= now
                        )
                    )
                )
            ).order_by(Subscription.expires_at.desc())
        )
        return list(result.scalars().all())