from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Payment, PaymentTransaction, PaymentStatus
from app.database.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Payment, session)

    async def create(self, user_id: int, plan_id: int, amount: int,
                     currency: str = "INR", payment_method: str = "upi",
                     notes: str | None = None) -> Payment:
        payment = Payment(
            user_id=user_id,
            plan_id=plan_id,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            notes=notes,
            status=PaymentStatus.PENDING,
        )
        await self.add(payment)
        return payment

    async def get_by_id(self, payment_id: int) -> Optional[Payment]:
        return await self.get(payment_id)

    async def get_pending(self, limit: int = 100, offset: int = 0) -> List[Payment]:
        result = await self.session.execute(
            select(Payment).where(Payment.status == PaymentStatus.PENDING)
            .order_by(Payment.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def get_user_payments(self, user_id: int, limit: int = 50) -> List[Payment]:
        result = await self.session.execute(
            select(Payment).where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def transaction_id_exists(self, transaction_id: str) -> bool:
        result = await self.session.execute(
            select(func.count()).select_from(PaymentTransaction).where(
                PaymentTransaction.transaction_id == transaction_id
            )
        )
        return result.scalar_one() > 0

    async def approve(self, payment_id: int, admin_id: int,
                      transaction_id: str, utr_number: str | None = None,
                      sender_name: str | None = None,
                      sender_upi_id: str | None = None) -> Optional[Payment]:
        payment = await self.get_by_id(payment_id)
        if not payment or payment.status != PaymentStatus.PENDING:
            return None

        # Add transaction record
        txn = PaymentTransaction(
            payment_id=payment.id,
            transaction_id=transaction_id,
            utr_number=utr_number,
            sender_name=sender_name,
            sender_upi_id=sender_upi_id,
            amount=payment.amount,
            status="approved",
        )
        self.session.add(txn)

        payment.status = PaymentStatus.APPROVED
        payment.approved_by = admin_id
        payment.approved_at = datetime.now(timezone.utc)
        await self.flush()
        return payment

    async def reject(self, payment_id: int, admin_id: int, reason: str | None = None) -> Optional[Payment]:
        payment = await self.get_by_id(payment_id)
        if not payment or payment.status != PaymentStatus.PENDING:
            return None

        payment.status = PaymentStatus.REJECTED
        payment.notes = (payment.notes or "") + f"\nRejected: {reason}" if reason else payment.notes
        await self.flush()
        return payment