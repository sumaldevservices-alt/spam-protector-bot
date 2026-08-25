from sqlalchemy import BigInteger, ForeignKey, String, Text, DateTime, Enum as SQLEnum, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base
import enum


class ModerationAction(str, enum.Enum):
    DELETE_LINK = "delete_link"
    DELETE_SPAM = "delete_spam"
    DELETE_DUPLICATE = "delete_duplicate"
    DELETE_LOCK = "delete_lock"
    DELETE_MANUAL = "delete_manual"
    WARN_USER = "warn_user"
    BAN_USER = "ban_user"


class ModerationLog(Base):
    __tablename__ = "moderation_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    action: Mapped[ModerationAction] = mapped_column(SQLEnum(ModerationAction), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    deleted_by_bot: Mapped[bool] = mapped_column(default=True, nullable=False)
    timestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    channel: Mapped["Channel"] = relationship("Channel", back_populates="moderation_logs")

    def __repr__(self) -> str:
        return f"<ModerationLog(id={self.id}, channel_id={self.channel_id}, action={self.action})>"