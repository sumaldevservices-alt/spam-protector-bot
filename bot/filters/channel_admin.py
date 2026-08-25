from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession


class IsChannelAdminFilter(BaseFilter):
    """Check if user is admin of the channel."""

    def __init__(self):
        pass

    async def __call__(self, event: Message | CallbackQuery, bot: Bot, session: AsyncSession) -> bool:
        if isinstance(event, Message):
            chat = event.chat
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            chat = event.message.chat if event.message else None
            user = event.from_user
        else:
            return False

        if not chat or not user:
            return False

        # For private chats (bot PM), always allow
        if chat.type == "private":
            return True

        try:
            member = await bot.get_chat_member(chat_id=chat.id, user_id=user.id)
            return member.status in ("administrator", "creator")
        except Exception:
            return False


class IsChannelOwnerFilter(BaseFilter):
    """Check if user is the owner of the channel (from our DB)."""

    async def __call__(self, event: Message | CallbackQuery, session: AsyncSession) -> bool:
        from app.services.channels import ChannelService
        from app.config import settings

        if isinstance(event, Message):
            chat = event.chat
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            chat = event.message.chat if event.message else None
            user = event.from_user
        else:
            return False

        if not chat or not user:
            return False

        # For private chats, check via callback data or state
        if chat.type == "private":
            return True

        channel_service = ChannelService(session, event.bot if hasattr(event, 'bot') else None)
        # We need the bot instance - this will be handled in handlers
        return False  # Actual check done in handlers


class IsSuperAdminFilter(BaseFilter):
    """Check if user is super admin."""

    def __init__(self):
        pass

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user if hasattr(event, 'from_user') else None
        if not user:
            return False
        from app.config import settings
        return user.id in settings.SUPER_ADMIN_IDS


class HasActiveSubscriptionFilter(BaseFilter):
    """Check if user has active subscription for the channel."""

    async def __call__(self, event: Message | CallbackQuery, session: AsyncSession) -> bool:
        from app.services.subscriptions import SubscriptionService

        user = event.from_user
        if not user:
            return False

        if isinstance(event, Message) and event.chat.type != "private":
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery):
            # Extract from callback data or state
            chat_id = None
        else:
            return True  # Private messages allowed

        if not chat_id:
            return True

        sub_service = SubscriptionService(session)
        plan = await sub_service.get_effective_plan_for_channel(chat_id)
        return plan is not None