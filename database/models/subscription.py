from sqlalchemy import BigInteger, ForeignKey, DateTime, Enum as SQLEnum, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base
import enum


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"
    TRIAL = "trial"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    channel_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("channels.id"), nullable=True, index=True)
    status: Mapped[SubscriptionStatus] = mapped_column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.PENDING, nullable=False)
    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    channel_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    auto_renew: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
    plan: Mapped["Plan"] = relationship("Plan", back_populates="subscriptions")
    channel: Mapped["Channel | None"] = relationship("Channel", back_populates="subscriptions")
    payment: Mapped["Payment | None"] = relationship("Payment", back_populates="subscription", uselist=False)

    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", name="uq_user_channel_subscription"),
    )

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, plan_id={self.plan_id}, status={self.status})>"