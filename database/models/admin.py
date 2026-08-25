from sqlalchemy import BigInteger, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base
import enum


class AdminRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    SUPPORT = "support"


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[AdminRole] = mapped_column(SQLEnum(AdminRole), default=AdminRole.ADMIN, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    added_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("admins.id"), nullable=True)

    # Relationships
    approved_payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="admin", foreign_keys="Payment.approved_by")

    def __repr__(self) -> str:
        return f"<Admin(id={self.id}, telegram_id={self.telegram_id}, role={self.role})>"