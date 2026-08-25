from typing import Optional, List
from aiogram import Bot
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Channel, ChannelStatus, User
from app.database.repositories import ChannelRepository, UserRepository
from app.services.subscriptions import SubscriptionService
from app.config import settings


class ChannelService:
    def __init__(self, session: AsyncSession, bot: Bot):
        self.session = session
        self.bot = bot
        self.channel_repo = ChannelRepository(session)
        self.user_repo = UserRepository(session)
        self.sub_service = SubscriptionService(session)

    async def validate_bot_admin_permissions(self, chat_id: int) -> tuple[bool, bool]:
        """
        Check if bot is admin in channel and has delete permissions.
        Returns (is_admin, can_delete_messages).
        """
        try:
            bot_member = await self.bot.get_chat_member(chat_id=chat_id, user_id=self.bot.id)
            is_admin = bot_member.status in ("administrator", "creator")
            can_delete = getattr(bot_member, "can_delete_messages", False) if is_admin else False
            return is_admin, can_delete
        except Exception as e:
            print(f"Error checking bot permissions: {e}")
            return False, False

    async def add_channel(self, user_id: int, chat_id: int, title: str,
                          username: str | None = None, invite_link: str | None = None) -> Channel:
        """Add or update a channel for a user."""
        # Check if channel already exists
        existing = await self.channel_repo.get_by_chat_id(chat_id)
        if existing:
            # Update if needed
            existing.title = title
            existing.username = username
            existing.invite_link = invite_link
            if existing.owner_user_id != user_id:
                existing.owner_user_id = user_id
            await self.channel_repo.flush()
            return existing

        # Check subscription limits
        can_add, reason = await self.sub_service.can_add_channel(user_id, chat_id)
        if not can_add:
            raise ValueError(reason)

        # Create channel
        channel = await self.channel_repo.create(
            telegram_chat_id=chat_id,
            title=title,
            owner_user_id=user_id,
            username=username,
            invite_link=invite_link,
        )

        # Check bot permissions
        is_admin, can_delete = await self.validate_bot_admin_permissions(chat_id)
        await self.channel_repo.update_admin_perms(chat_id, is_admin, can_delete)

        # Activate free trial if first channel
        active_subs = await self.sub_service.sub_repo.get_active_for_user(user_id)
        if not active_subs:
            await self.sub_service.activate_free_trial(user_id, chat_id)

        await self.channel_repo.commit()
        return channel

    async def get_user_channels(self, user_id: int) -> List[Channel]:
        """Get all channels for a user with their subscription status."""
        channels = await self.channel_repo.get_user_channels(user_id)
        return channels

    async def verify_channel_ownership(self, user_id: int, chat_id: int) -> bool:
        """Verify user owns the channel."""
        channel = await self.channel_repo.get_by_chat_id(chat_id)
        return channel is not None and channel.owner_user_id == user_id

    async def update_channel_permissions(self, chat_id: int) -> tuple[bool, bool]:
        """Re-verify and update bot permissions for a channel."""
        is_admin, can_delete = await self.validate_bot_admin_permissions(chat_id)
        await self.channel_repo.update_admin_perms(chat_id, is_admin, can_delete)
        await self.channel_repo.commit()
        return is_admin, can_delete

    async def remove_channel(self, user_id: int, chat_id: int) -> bool:
        """Remove a channel from user's management (soft delete)."""
        channel = await self.channel_repo.get_by_chat_id(chat_id)
        if channel and channel.owner_user_id == user_id:
            channel.status = ChannelStatus.INACTIVE
            await self.channel_repo.commit()
            return True
        return False

    async def notify_super_admins(self, text: str, reply_markup=None):
        """Send notification to all super admins."""
        for admin_id in settings.SUPER_ADMIN_IDS:
            try:
                await self.bot.send_message(admin_id, text, reply_markup=reply_markup, parse_mode="HTML")
            except Exception as e:
                print(f"Failed to notify admin {admin_id}: {e}")

    async def get_channel_with_subscription(self, chat_id: int):
        """Get channel with its active subscription."""
        channel = await self.channel_repo.get_by_chat_id(chat_id)
        if not channel:
            return None, None

        sub = await self.sub_service.get_effective_plan_for_channel(channel.telegram_chat_id)
        return channel, sub