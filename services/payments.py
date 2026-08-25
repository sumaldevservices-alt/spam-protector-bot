from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Payment, PaymentTransaction, Plan, PaymentStatus, SubscriptionStatus, ChannelStatus
from app.database.repositories import PaymentRepository, PlanRepository, SubscriptionRepository, ChannelRepository
from app.services.subscriptions import SubscriptionService


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.plan_repo = PlanRepository(session)
        self.sub_repo = SubscriptionRepository(session)
        self.channel_repo = ChannelRepository(session)
        self.sub_service = SubscriptionService(session)

    async def create_payment_request(self, user_id: int, plan_id: int) -> Optional[Payment]:
        """Create a pending payment request."""
        plan = await self.plan_repo.get_by_id(plan_id)
        if not plan or not plan.is_active:
            return None

        payment = await self.payment_repo.create(
            user_id=user_id,
            plan_id=plan_id,
            amount=plan.price,
        )
        await self.payment_repo.commit()
        return payment

    async def validate_transaction_id(self, transaction_id: str) -> bool:
        """Check if transaction ID is already used."""
        return not await self.payment_repo.transaction_id_exists(transaction_id)

    async def submit_transaction(self, payment_id: int, transaction_id: str,
                                  utr_number: str | None = None,
                                  sender_name: str | None = None,
                                  sender_upi_id: str | None = None) -> Optional[Payment]:
        """Submit transaction ID for a pending payment."""
        payment = await self.payment_repo.get_by_id(payment_id)
        if not payment or payment.status != PaymentStatus.PENDING:
            return None

        # Check transaction ID uniqueness
        if await self.payment_repo.transaction_id_exists(transaction_id):
            return None

        # Add transaction record
        txn = PaymentTransaction(
            payment_id=payment.id,
            transaction_id=transaction_id,
            utr_number=utr_number,
            sender_name=sender_name,
            sender_upi_id=sender_upi_id,
            amount=payment.amount,
            status="submitted",
        )
        self.session.add(txn)
        await self.payment_repo.flush()

        return payment

    async def approve_payment(self, payment_id: int, admin_id: int,
                               transaction_id: str, utr_number: str | None = None,
                               sender_name: str | None = None,
                               sender_upi_id: str | None = None,
                               channel_id: int | None = None) -> Optional[Payment]:
        """
        Approve payment and activate subscription.
        Runs in a transaction to ensure consistency.
        """
        # Double-check transaction ID hasn't been approved already
        if await self.payment_repo.transaction_id_exists(transaction_id):
            # Check if it was already approved for another payment
            result = await self.session.execute(
                select(PaymentTransaction).where(
                    PaymentTransaction.transaction_id == transaction_id,
                    PaymentTransaction.status == "approved"
                )
            )
            if result.scalar_one_or_none():
                return None  # Already used and approved

        payment = await self.payment_repo.get_by_id(payment_id)
        if not payment or payment.status != PaymentStatus.PENDING:
            return None

        # Approve the payment
        payment = await self.payment_repo.approve(
            payment_id=payment_id,
            admin_id=admin_id,
            transaction_id=transaction_id,
            utr_number=utr_number,
            sender_name=sender_name,
            sender_upi_id=sender_upi_id,
        )
        if not payment:
            return None

        # Activate subscription
        subscription = await self.sub_service.activate_subscription(
            user_id=payment.user_id,
            plan_id=payment.plan_id,
            channel_id=channel_id,
        )
        if subscription:
            payment.subscription_id = subscription.id
            await self.payment_repo.flush()

        await self.payment_repo.commit()
        return payment

    async def reject_payment(self, payment_id: int, admin_id: int, reason: str | None = None) -> Optional[Payment]:
        """Reject a pending payment."""
        payment = await self.payment_repo.reject(payment_id, admin_id, reason)
        if payment:
            await self.payment_repo.commit()
        return payment

    async def get_pending_payments(self, limit: int = 100, offset: int = 0):
        """Get all pending payments for admin review."""
        return await self.payment_repo.get_pending(limit, offset)

    async def get_payment_with_details(self, payment_id: int) -> Optional[Payment]:
        """Get payment with all related data loaded."""
        payment = await self.payment_repo.get_by_id(payment_id)
        if payment:
            # Load related objects
            await self.session.refresh(payment, ["user", "plan", "subscription", "transactions"])
        return payment

    async def get_user_payment_history(self, user_id: int, limit: int = 20):
        return await self.payment_repo.get_user_payments(user_id, limit)