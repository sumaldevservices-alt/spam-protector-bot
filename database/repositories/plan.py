from typing import Optional, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Plan
from app.database.repositories.base import BaseRepository


class PlanRepository(BaseRepository[Plan]):
    def __init__(self, session: AsyncSession):
        super().__init__(Plan, session)

    async def create(self, name: str, display_name: str, price: int, duration_days: int,
                     channel_limit: int, features: dict | None = None,
                     description: str | None = None, is_active: bool = True,
                     sort_order: int = 0) -> Plan:
        plan = Plan(
            name=name,
            display_name=display_name,
            price=price,
            duration_days=duration_days,
            channel_limit=channel_limit,
            features=features or {},
            description=description,
            is_active=is_active,
            sort_order=sort_order,
        )
        await self.add(plan)
        return plan

    async def get_all_active(self, limit: int = 100, offset: int = 0) -> List[Plan]:
        result = await self.session.execute(
            select(Plan).where(Plan.is_active == True).order_by(Plan.sort_order).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Plan]:
        result = await self.session.execute(
            select(Plan).order_by(Plan.sort_order).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_id(self, plan_id: int) -> Optional[Plan]:
        return await self.get(plan_id)

    async def update(self, plan_id: int, **kwargs) -> Optional[Plan]:
        plan = await self.get_by_id(plan_id)
        if plan:
            for key, value in kwargs.items():
                if hasattr(plan, key):
                    setattr(plan, key, value)
            await self.flush()
            return plan
        return None

    async def delete(self, plan_id: int) -> bool:
        plan = await self.get_by_id(plan_id)
        if plan:
            await self.delete(plan)
            return True
        return False

    async def toggle_active(self, plan_id: int) -> Optional[Plan]:
        plan = await self.get_by_id(plan_id)
        if plan:
            plan.is_active = not plan.is_active
            await self.flush()
            return plan
        return None

    async def seed_default_plans(self) -> None:
        """Seed default plans if table is empty."""
        existing = await self.count()
        if existing > 0:
            return

        plans = [
            {
                "name": "free_trial",
                "display_name": "Free Trial",
                "price": 0,
                "duration_days": 3,
                "channel_limit": 1,
                "features": {"features": ["Basic protection", "1 channel"]},
                "description": "Free trial for new users",
                "is_active": True,
                "sort_order": 0,
            },
            {
                "name": "1_day",
                "display_name": "1 Day",
                "price": 1500,  # ₹15 in paise
                "duration_days": 1,
                "channel_limit": 1,
                "features": {"features": [
                    "/lock", "/nolink", "Basic anti-spam",
                    "Repeated message detection", "Protection logs"
                ]},
                "description": "24 hours protection for 1 channel",
                "is_active": True,
                "sort_order": 1,
            },
            {
                "name": "1_week",
                "display_name": "1 Week",
                "price": 7000,  # ₹70 in paise
                "duration_days": 7,
                "channel_limit": 2,
                "features": {"features": [
                    "Everything from 1 Day", "Stronger spam detection",
                    "Auto-delete", "Advanced link protection", "Channel activity logs"
                ]},
                "description": "7 days protection for 2 channels",
                "is_active": True,
                "sort_order": 2,
            },
            {
                "name": "1_month",
                "display_name": "1 Month",
                "price": 19900,  # ₹199 in paise
                "duration_days": 30,
                "channel_limit": 3,
                "features": {"features": [
                    "All protection features", "/lock", "/nolink",
                    "Advanced spam detection", "Duplicate detection",
                    "Logs", "Priority support"
                ]},
                "description": "30 days protection for 3 channels",
                "is_active": True,
                "sort_order": 3,
            },
            {
                "name": "pro",
                "display_name": "Pro",
                "price": 49900,  # ₹499 in paise
                "duration_days": 30,
                "channel_limit": 10,
                "features": {"features": [
                    "Everything", "Advanced controls", "Priority support",
                    "Detailed analytics", "Custom rules"
                ]},
                "description": "30 days protection for 10 channels",
                "is_active": True,
                "sort_order": 4,
            },
        ]

        for p in plans:
            await self.create(**p)