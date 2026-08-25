from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import (
    User, Channel, Plan, Subscription, Payment, PaymentStatus,
    SubscriptionStatus, ChannelStatus, Admin, AdminRole, BannedUser
)
from app.database.repositories import (
    UserRepository, ChannelRepository, PlanRepository,
    SubscriptionRepository, PaymentRepository, AdminRepository,
    BannedUserRepository
)
from app.config import settings


class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.channel_repo = ChannelRepository(session)
        self.plan_repo = PlanRepository(session)
        self.sub_repo = SubscriptionRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.admin_repo = AdminRepository(session)
        self.ban_repo = BannedUserRepository(session)

    # ===== User Management =====

    async def search_users(self, query: str, limit: int = 50) -> List[User]:
        """Search users by ID or username."""
        try:
            user_id = int(query)
            user = await self.user_repo.get_by_telegram_id(user_id)
            return [user] if user else []
        except ValueError:
            return await self.user_repo.search_by_username(query, limit)

    async def get_user_details(self, user_id: int) -> dict:
        """Get comprehensive user details for admin panel."""
        user = await self.user_repo.get_by_telegram_id(user_id)
        if not user:
            return {}

        channels = await self.channel_repo.get_user_channels(user_id)
        active_subs = await self.sub_repo.get_active_for_user(user_id)
        payments = await self.payment_repo.get_user_payments(user_id, 10)
        is_banned = await self.ban_repo.is_banned(user_id)

        return {
            "user": user,
            "channels": channels,
            "active_subscriptions": active_subs,
            "recent_payments": payments,
            "is_banned": is_banned,
            "total_channels": len(channels),
            "active_channels": len([c for c in channels if c.status == ChannelStatus.ACTIVE]),
        }

    async def add_subscription_days(self, user_id: int, days: int, admin_id: int) -> Optional[Subscription]:
        """Add days to user's active subscription."""
        active_subs = await self.sub_repo.get_active_for_user(user_id)
        if not active_subs:
            return None

        # Extend the most recent active subscription
        sub = active_subs[0]
        sub.expires_at = sub.expires_at + timedelta(days=days)
        sub.updated_at = datetime.now(timezone.utc)
        await self.sub_repo.commit()
        return sub

    async def upgrade_plan(self, user_id: int, new_plan_id: int, admin_id: int) -> Optional[Subscription]:
        """Upgrade user to a new plan."""
        plan = await self.plan_repo.get_by_id(new_plan_id)
        if not plan:
            return None

        active_subs = await self.sub_repo.get_active_for_user(user_id)
        if not active_subs:
            return None

        sub = active_subs[0]
        sub.plan_id = new_plan_id
        sub.channel_limit = plan.channel_limit
        sub.updated_at = datetime.now(timezone.utc)
        await self.sub_repo.commit()
        return sub

    async def cancel_subscription(self, user_id: int, admin_id: int) -> bool:
        """Cancel all active subscriptions for a user."""
        active_subs = await self.sub_repo.get_active_for_user(user_id)
        for sub in active_subs:
            sub.status = SubscriptionStatus.CANCELLED
            sub.updated_at = datetime.now(timezone.utc)
        await self.sub_repo.commit()
        return True

    async def ban_user(self, user_id: int, username: str | None, reason: str,
                        admin_id: int, is_permanent: bool = True,
                        expires_at: datetime | None = None) -> BannedUser:
        """Ban a user."""
        banned = await self.ban_repo.ban(user_id, username, reason, admin_id, is_permanent, expires_at)
        user = await self.user_repo.get_by_telegram_id(user_id)
        if user:
            user.is_banned = True
        await self.session.commit()
        return banned

    async def unban_user(self, user_id: int, admin_id: int) -> bool:
        """Unban a user."""
        success = await self.ban_repo.unban(user_id)
        if success:
            user = await self.user_repo.get_by_telegram_id(user_id)
            if user:
                user.is_banned = False
            await self.session.commit()
        return success

    # ===== Plan Management =====

    async def create_plan(self, name: str, display_name: str, price: int,
                          duration_days: int, channel_limit: int,
                          features: dict, admin_id: int) -> Plan:
        """Create a new plan."""
        plan = await self.plan_repo.create(
            name=name,
            display_name=display_name,
            price=price,
            duration_days=duration_days,
            channel_limit=channel_limit,
            features=features,
            is_active=True,
        )
        return plan

    async def update_plan(self, plan_id: int, **kwargs) -> Optional[Plan]:
        """Update plan details."""
        return await self.plan_repo.update(plan_id, **kwargs)

    async def delete_plan(self, plan_id: int) -> bool:
        """Delete (deactivate) a plan."""
        plan = await self.plan_repo.get_by_id(plan_id)
        if plan:
            plan.is_active = False
            await self.plan_repo.commit()
            return True
        return False

    async def get_all_plans(self, include_inactive: bool = False) -> List[Plan]:
        """Get all plans."""
        return await self.plan_repo.get_all(include_inactive=include_inactive)

    # ===== Payment Management =====

    async def get_pending_payments(self, limit: int = 100) -> List[Payment]:
        """Get payments pending review."""
        return await self.payment_repo.get_pending(limit)

    async def approve_payment(self, payment_id: int, admin_id: int,
                              transaction_id: str, channel_id: int | None = None,
                              utr_number: str | None = None,
                              sender_name: str | None = None,
                              sender_upi_id: str | None = None) -> Optional[Payment]:
        """Approve a pending payment."""
        from app.services.payments import PaymentService
        payment_service = PaymentService(self.session)
        return await payment_service.approve_payment(
            payment_id=payment_id,
            admin_id=admin_id,
            transaction_id=transaction_id,
            utr_number=utr_number,
            sender_name=sender_name,
            sender_upi_id=sender_upi_id,
            channel_id=channel_id,
        )

    async def reject_payment(self, payment_id: int, admin_id: int, reason: str) -> Optional[Payment]:
        """Reject a pending payment."""
        from app.services.payments import PaymentService
        payment_service = PaymentService(self.session)
        return await payment_service.reject_payment(payment_id, admin_id, reason)

    # ===== Statistics =====

    async def get_statistics(self) -> dict:
        """Get system statistics for admin dashboard."""
        total_users = await self.user_repo.count()
        total_channels = await self.channel_repo.count()
        active_channels = await self.channel_repo.count_by_status(ChannelStatus.ACTIVE)
        total_subscriptions = await self.sub_repo.count_active()
        pending_payments = await self.payment_repo.count_pending()
        total_revenue = await self.payment_repo.get_total_revenue()

        return {
            "total_users": total_users,
            "total_channels": total_channels,
            "active_channels": active_channels,
            "active_subscriptions": total_subscriptions,
            "pending_payments": pending_payments,
            "total_revenue": total_revenue,
        }

    # ===== Broadcast =====

    async def broadcast_message(self, text: str, target: str = "all") -> dict:
        """Broadcast message to users. Target: 'all', 'active', 'expired'."""
        users = []
        if target == "all":
            users = await self.user_repo.get_all(limit=10000)
        elif target == "active":
            users = await self.user_repo.get_with_active_subscription()
        elif target == "expired":
            users = await self.user_repo.get_with_expired_subscription()

        sent = 0
        failed = 0
        for user in users:
            try:
                # This would be called from bot context
                # await self.bot.send_message(user.telegram_id, text)
                sent += 1
            except Exception:
                failed += 1

        return {"sent": sent, "failed": failed, "total": len(users)}

    # ===== Admin Management =====

    async def add_admin(self, telegram_id: int, username: str | None,
                        role: AdminRole = AdminRole.ADMIN) -> Admin:
        """Add a new admin."""
        return await self.admin_repo.add_admin(telegram_id, username, role)

    async def remove_admin(self, telegram_id: int) -> bool:
        """Remove an admin."""
        return await self.admin_repo.remove_admin(telegram_id)

    async def list_admins(self) -> List[Admin]:
        """List all active admins."""
        return await self.admin_repo.list_admins()