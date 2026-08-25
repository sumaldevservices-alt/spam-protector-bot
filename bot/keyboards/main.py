from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import settings


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Add Channel", callback_data="add_channel"),
        InlineKeyboardButton(text="💳 Buy Plan", callback_data="buy_plan"),
    )
    builder.row(
        InlineKeyboardButton(text="📺 My Channels", callback_data="my_channels"),
        InlineKeyboardButton(text="⚙️ Settings", callback_data="settings"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Statistics", callback_data="stats"),
        InlineKeyboardButton(text="❓ Help", callback_data="help"),
    )
    return builder.as_markup()


def get_buy_plan_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1 Day — ₹15", callback_data="plan_select:day_1"),
        InlineKeyboardButton(text="1 Week — ₹70", callback_data="plan_select:week_1"),
    )
    builder.row(
        InlineKeyboardButton(text="1 Month — ₹199", callback_data="plan_select:month_1"),
        InlineKeyboardButton(text="Pro — ₹499", callback_data="plan_select:pro"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="back_main"),
    )
    return builder.as_markup()


def get_payment_keyboard(plan_key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Copy UPI ID", callback_data=f"copy_upi:{plan_key}"),
    )
    builder.row(
        InlineKeyboardButton(text="📸 I've Paid", callback_data=f"payment_paid:{plan_key}"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="buy_plan"),
    )
    return builder.as_markup()


def get_my_channels_keyboard(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        status_emoji = "🟢" if ch["status"] == "active" else "🔴"
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} {ch['title']} ({ch['plan']})",
                callback_data=f"channel_manage:{ch['chat_id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="back_main"),
    )
    return builder.as_markup()


def get_channel_settings_keyboard(channel_id: int, settings: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    lock_status = "🔒 ON" if settings.get("lock_enabled") else "🔓 OFF"
    nolink_status = "🔗 ON" if settings.get("nolink_enabled") else "🔓 OFF"
    spam_status = "🛡 ON" if settings.get("anti_spam_enabled") else "🛡 OFF"
    dup_status = "📝 ON" if settings.get("duplicate_enabled") else "📝 OFF"

    builder.row(
        InlineKeyboardButton(text=f"🔒 Lock: {lock_status}", callback_data=f"toggle_lock:{channel_id}"),
    )
    builder.row(
        InlineKeyboardButton(text=f"🔗 No Link: {nolink_status}", callback_data=f"toggle_nolink:{channel_id}"),
    )
    builder.row(
        InlineKeyboardButton(text=f"{spam_status} Anti-Spam", callback_data=f"toggle_spam:{channel_id}"),
        InlineKeyboardButton(text=f"{dup_status} Duplicates", callback_data=f"toggle_dup:{channel_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Logs", callback_data=f"view_logs:{channel_id}"),
        InlineKeyboardButton(text="🗑 Purge Settings", callback_data=f"purge_settings:{channel_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="my_channels"),
    )
    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Users", callback_data="admin_users"),
        InlineKeyboardButton(text="📺 Channels", callback_data="admin_channels"),
    )
    builder.row(
        InlineKeyboardButton(text="💳 Payments", callback_data="admin_payments"),
        InlineKeyboardButton(text="📦 Plans", callback_data="admin_plans"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Statistics", callback_data="admin_stats"),
        InlineKeyboardButton(text="🎁 Add Days", callback_data="admin_add_days"),
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Ban User", callback_data="admin_ban"),
        InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Settings", callback_data="admin_settings"),
    )
    return builder.as_markup()


def get_admin_payment_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Approve", callback_data=f"admin_approve_pay:{payment_id}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"admin_reject_pay:{payment_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔎 View User", callback_data=f"admin_view_user:{payment_id}"),
        InlineKeyboardButton(text="⬅️ Back", callback_data="admin_payments"),
    )
    return builder.as_markup()


def get_link_sensitivity_keyboard(current: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for level in ["strict", "normal", "relaxed"]:
        mark = "✅ " if level == current else ""
        builder.row(
            InlineKeyboardButton(text=f"{mark}{level.capitalize()}", callback_data=f"set_sensitivity:{level}"),
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Back", callback_data="channel_settings"),
    )
    return builder.as_markup()


def get_confirm_keyboard(action: str, item_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_{action}:{item_id}"),
        InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_{action}:{item_id}"),
    )
    return builder.as_markup()