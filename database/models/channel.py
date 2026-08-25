from sqlalchemy import BigInteger, String, Boolean, ForeignKey, DateTime, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base
import enum


class ChannelStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PENDING = "pending"
    INACTIVE = "inactive"


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    status: Mapped[ChannelStatus] = mapped_column(SQLEnum(ChannelStatus), default=ChannelStatus.PENDING, nullable=False)
    bot_is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_delete_messages: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    invite_link: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="channels", foreign_keys=[owner_user_id])
    settings: Mapped["ChannelSettings"] = relationship("ChannelSettings", back_populates="channel", uselist=False, cascade="all, delete-orphan")
    subscriptions: Mapped[list["Subscription"]] = relationship("Subscription", back_populates="channel")
    moderation_logs: Mapped[list["ModerationLog"]] = relationship("ModerationLog", back_populates="channel")

    def __repr__(self) -> str:
        return f"<Channel(id={self.id}, chat_id={self.telegram_chat_id}, title={self.title}, status={self.status})>"