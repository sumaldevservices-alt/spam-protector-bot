from sqlalchemy import String, Integer, Boolean, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models.base import Base
import enum


class PlanDurationUnit(str, enum.Enum):
    DAYS = "days"
    MONTHS = "months"


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # in paise (₹1 = 100 paise)
    duration_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    channel_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    features: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    subscriptions: Mapped[list["Subscription"]] = relationship("Subscription", back_populates="plan")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="plan")

    def __repr__(self) -> str:
        return f"<Plan(id={self.id}, name={self.name}, price={self.price}, channel_limit={self.channel_limit})>"

    @property
    def price_inr(self) -> float:
        return self.price / 100

    @property
    def feature_list(self) -> list[str]:
        return self.features.get("features", [])