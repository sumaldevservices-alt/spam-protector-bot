from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.main import get_main_menu_keyboard
from app.database.repositories.user import UserRepository

router = Router()

WELCOME_TEXT = """
🛡 <b>Welcome to ChannelGuard AI</b>

Protect your Telegram channel from:
🚫 Spam
🔗 Unwanted Links
🔒 Unauthorized Posting
⚡ Message Flooding
📨 Repeated Messages

<i>The smartest channel protection bot on Telegram.</i>

Get started by adding your channel below 👇
"""


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, **kwargs):
    """Handle /start command."""
    user = message.from_user
    if not user:
        return

    # Register or update user
    user_repo = UserRepository(session)
    db_user = await user_repo.get_by_telegram_id(user.id)
    if not db_user:
        await user_repo.create(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code,
        )
    else:
        db_user.username = user.username
        db_user.first_name = user.first_name
        db_user.last_name = user.last_name

    await message.answer(WELCOME_TEXT, parse_mode="HTML", reply_markup=get_main_menu_keyboard())


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery, **kwargs):
    """Return to main menu."""
    await callback.message.edit_text(WELCOME_TEXT, parse_mode="HTML", reply_markup=get_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery, **kwargs):
    """Show help information."""
    text = """
❓ <b>ChannelGuard AI — Help</b>

<b>Commands:</b>
/start — Main menu
/lock — Enable channel lock mode
/lockoff — Disable channel lock
/nolink — Enable link protection
/nolinkoff — Disable link protection
/status — View channel protection status
/settings — Channel settings
/plan — View subscription plans
/channels — My protected channels
/help — This help message

<b>How to get started:</b>

1️⃣ Click <b>Add Channel</b> to register your channel
2️⃣ Make the bot an admin with <b>Delete Messages</b> permission
3️⃣ Choose a subscription plan
4️⃣ Complete payment
5️⃣ Activate protection features

<b>Protection Features:</b>
🔒 <b>Lock Mode</b> — Restrict posting in your channel
🔗 <b>No Link Mode</b> — Auto-delete messages with links
🚫 <b>Anti-Spam</b> — Detect and remove spam posts
📝 <b>Duplicate Protection</b> — Remove repeated messages

Need help? Contact the admin.
"""
    from app.bot.keyboards.main import get_main_menu_keyboard
    builder = get_main_menu_keyboard()
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder)
    await callback.answer()


@router.message(F.text == "/help")
async def cmd_help(message: Message, **kwargs):
    """Handle /help command."""
    text = """
❓ <b>ChannelGuard AI — Help</b>

<b>Commands:</b>
/start — Main menu
/lock — Enable channel lock mode
/lockoff — Disable channel lock
/nolink — Enable link protection
/nolinkoff — Disable link protection
/status — View channel protection status
/settings — Channel settings
/plan — View subscription plans
/channels — My protected channels
/help — This help message

<b>How to get started:</b>

1️⃣ Add the bot to your channel as admin
2️⃣ Click /start in private chat
3️⃣ Add your channel
4️⃣ Choose & pay for a plan
5️⃣ Activate protection!
"""
    await message.answer(text, parse_mode="HTML")