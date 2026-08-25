from sqlalchemy import BigInteger, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base


class BannedUser(Base):
    __tablename__ = "banned_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    banned_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("admins.id"), nullable=False)
    is_permanent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    admin: Mapped["Admin"] = relationship("Admin", foreign_keys=[banned_by])

    def __repr__(self) -> str:
        return f"<BannedUser(id={self.id}, telegram_id={self.telegram_id}, active={self.is_active})>"