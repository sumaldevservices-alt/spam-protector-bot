from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, DateTime, Enum as SQLEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base
import enum


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id"), nullable=True, unique=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # in paise
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(50), default="upi", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("admins.id"), nullable=True)
    approved_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="payments")
    plan: Mapped["Plan"] = relationship("Plan", back_populates="payments")
    subscription: Mapped["Subscription | None"] = relationship("Subscription", back_populates="payment")
    transactions: Mapped[list["PaymentTransaction"]] = relationship("PaymentTransaction", back_populates="payment", cascade="all, delete-orphan")
    admin: Mapped["Admin | None"] = relationship("Admin", foreign_keys=[approved_by])

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, user_id={self.user_id}, amount={self.amount}, status={self.status})>"


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    utr_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender_upi_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="submitted", nullable=False)
    raw_data: Mapped[dict | None] = mapped_column(nullable=True)

    # Relationships
    payment: Mapped["Payment"] = relationship("Payment", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<PaymentTransaction(id={self.id}, payment_id={self.payment_id}, transaction_id={self.transaction_id})>"