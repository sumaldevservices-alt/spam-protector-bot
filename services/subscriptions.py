from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import (
    User, Channel, Plan, Subscription, SubscriptionStatus, ChannelStatus
)
from app.database.repositories import (
    UserRepository, ChannelRepository, PlanRepository,
    SubscriptionRepository, ChannelSettingsRepository
)
from app.config import settings


class SubscriptionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.channel_repo = ChannelRepository(session)
        self.plan_repo = PlanRepository(session)
        self.sub_repo = SubscriptionRepository(session)
        self.settings_repo = ChannelSettingsRepository(session)

    async def activate_free_trial(self, user_id: int, channel_id: int) -> Optional[Subscription]:
        """Activate free trial for user's first channel."""
        # Check if user already had a trial
        existing_trial = await self.sub_repo.get_active_for_user(user_id)
        trial_subs = [s for s in existing_trial if s.plan.name == "free_trial"]
        if trial_subs:
            return None  # Already used trial

        # Get free trial plan
        trial_plan = await self.session.execute(
            select(Plan).where(Plan.name == "free_trial", Plan.is_active == True)
        )
        trial_plan = trial_plan.scalar_one_or_none()
        if not trial_plan:
            return None

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.FREE_TRIAL_DAYS)

        subscription = await self.sub_repo.create(
            user_id=user_id,
            plan_id=trial_plan.id,
            channel_id=channel_id,
            status=SubscriptionStatus.TRIAL,
            started_at=now,
            expires_at=expires_at,
            channel_limit=trial_plan.channel_limit,
            auto_renew=False,
        )

        # Update channel status to active
        await self.channel_repo.set_status(channel_id, ChannelStatus.ACTIVE)

        await self.sub_repo.commit()
        return subscription

    async def activate_subscription(self, user_id: int, plan_id: int, channel_id: int | None = None) -> Optional[Subscription]:
        """Activate a paid subscription for a user/channel."""
        plan = await self.plan_repo.get_by_id(plan_id)
        if not plan or not plan.is_active:
            return None

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=plan.duration_days)

        subscription = await self.sub_repo.create(
            user_id=user_id,
            plan_id=plan_id,
            channel_id=channel_id,
            status=SubscriptionStatus.ACTIVE,
            started_at=now,
            expires_at=expires_at,
            channel_limit=plan.channel_limit,
            auto_renew=False,
        )

        # If channel specified, activate it
        if channel_id:
            await self.channel_repo.set_status(channel_id, ChannelStatus.ACTIVE)

        await self.sub_repo.commit()
        return subscription

    async def extend_subscription(self, subscription_id: int, days: int) -> Optional[Subscription]:
        """Extend subscription by N days."""
        sub = await self.sub_repo.extend(subscription_id, days)
        if sub:
            await self.sub_repo.commit()
        return sub

    async def get_effective_plan_for_channel(self, channel_id: int) -> Optional[Plan]:
        """Get the active plan covering this channel."""
        sub = await self.sub_repo.get_by_channel(channel_id)
        if sub:
            return await self.plan_repo.get_by_id(sub.plan_id)
        return None

    async def can_add_channel(self, user_id: int, requested_channel_id: int | None = None) -> tuple[bool, str]:
        """
        Check if user can add another channel.
        Returns (can_add, reason).
        """
        # Get active subscriptions
        active_subs = await self.sub_repo.get_active_for_user(user_id)
        if not active_subs:
            return False, "No active subscription"

        # Total channel limit across all active subscriptions
        total_limit = sum(s.channel_limit for s in active_subs)

        # Current active channels
        channels = await self.channel_repo.get_user_channels(user_id, active_only=True)
        current_count = len(channels)

        # If this channel is already registered, it doesn't count as new
        if requested_channel_id:
            for ch in channels:
                if ch.telegram_chat_id == requested_channel_id:
                    return True, "Channel already registered"

        if current_count >= total_limit:
            return False, f"Channel limit reached ({current_count}/{total_limit}). Upgrade your plan."

        return True, f"Can add channel ({current_count}/{total_limit})"

    async def expire_overdue(self) -> int:
        """Expire overdue subscriptions and update channel statuses."""
        expired_count = await self.sub_repo.expire_overdue()
        if expired_count > 0:
            await self.sub_repo.commit()

            # Update channel statuses for expired subscriptions
            # This is simplified - in reality we'd need to find channels for each expired sub
            # For now, rely on background worker to sync
        return expired_count

    async def get_user_subscription_summary(self, user_id: int) -> dict:
        """Get user's subscription status summary."""
        active = await self.sub_repo.get_active_for_user(user_id)
        expired = await self.sub_repo.get_expired_for_user(user_id)

        total_limit = sum(s.channel_limit for s in active)
        channels = await self.channel_repo.get_user_channels(user_id, active_only=True)

        return {
            "active_subscriptions": len(active),
            "total_channel_limit": total_limit,
            "active_channels": len(channels),
            "can_add_more": len(channels) < total_limit,
            "subscriptions": [
                {
                    "id": s.id,
                    "plan": s.plan.display_name if s.plan else "Unknown",
                    "status": s.status.value,
                    "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                    "channel_limit": s.channel_limit,
                    "channel_id": s.channel_id,
                }
                for s in active
            ],
            "expired_count": len(expired),
        }