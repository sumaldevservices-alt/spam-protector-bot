from sqlalchemy import BigInteger, ForeignKey, Boolean, Integer, String, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base
import enum


class LinkSensitivity(str, enum.Enum):
    STRICT = "strict"
    NORMAL = "normal"
    RELAXED = "relaxed"


class ChannelSettings(Base):
    __tablename__ = "channel_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Lock Mode
    lock_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lock_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Link Protection
    nolink_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    link_sensitivity: Mapped[LinkSensitivity] = mapped_column(SQLEnum(LinkSensitivity), default=LinkSensitivity.NORMAL, nullable=False)
    delete_links_silently: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_owner_links: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    whitelisted_domains: Mapped[dict] = mapped_column(JSON, default=lambda: {"domains": []}, nullable=False)
    link_warning_message: Mapped[str | None] = mapped_column(Text, default="🚫 Link detected — post deleted.", nullable=True)

    # Spam & Duplicate Protection
    anti_spam_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_threshold: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    duplicate_window_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # General
    log_actions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # Relationships
    channel: Mapped["Channel"] = relationship("Channel", back_populates="settings")

    def __repr__(self) -> str:
        return f"<ChannelSettings(channel_id={self.channel_id}, lock={self.lock_enabled}, nolink={self.nolink_enabled})>"