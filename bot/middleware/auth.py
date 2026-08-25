from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import async_session_maker
from app.config import settings


class DatabaseMiddleware(BaseMiddleware):
    """Provides database session to handlers."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session_maker() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


class AdminMiddleware(BaseMiddleware):
    """Checks if user is super admin."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None

        data["is_super_admin"] = user_id in settings.SUPER_ADMIN_IDS if user_id else False
        return await handler(event, data)


class BanCheckMiddleware(BaseMiddleware):
    """Checks if user is banned."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None

        if user_id:
            from app.database.repositories.banned_user import BannedUserRepository
            from app.database.session import async_session_maker

            async with async_session_maker() as session:
                repo = BannedUserRepository(session)
                data["is_banned"] = await repo.is_banned(user_id)
        else:
            data["is_banned"] = False

        if data.get("is_banned"):
            if isinstance(event, Message):
                await event.answer("🚫 You are banned from using this bot.")
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 You are banned from using this bot.", show_alert=True)
            return

        return await handler(event, data)


class ChannelOwnerMiddleware(BaseMiddleware):
    """Checks if user owns the channel (for channel-specific commands)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # This will be used in channel-specific handlers
        # The actual check is done in the handler using ChannelService
        return await handler(event, data)