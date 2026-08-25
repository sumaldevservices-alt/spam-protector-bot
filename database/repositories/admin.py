from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Admin, AdminRole
from app.database.repositories.base import BaseRepository


class AdminRepository(BaseRepository[Admin]):
    def __init__(self, session: AsyncSession):
        super().__init__(Admin, session)

    async def is_super_admin(self, telegram_id: int) -> bool:
        result = await self.session.execute(
            select(Admin).where(
                Admin.telegram_id == telegram_id,
                Admin.role == AdminRole.SUPER_ADMIN,
                Admin.is_active == True
            )
        )
        return result.scalar_one_or_none() is not None

    async def is_admin(self, telegram_id: int) -> bool:
        result = await self.session.execute(
            select(Admin).where(
                Admin.telegram_id == telegram_id,
                Admin.is_active == True
            )
        )
        return result.scalar_one_or_none() is not None

    async def add_admin(self, telegram_id: int, username: str | None,
                        role: AdminRole = AdminRole.ADMIN, added_by: int | None = None) -> Admin:
        admin = Admin(
            telegram_id=telegram_id,
            username=username,
            role=role,
            is_active=True,
            added_by=added_by,
        )
        await self.add(admin)
        return admin

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Admin]:
        result = await self.session.execute(
            select(Admin).where(Admin.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def list_admins(self, limit: int = 100, offset: int = 0) -> List[Admin]:
        result = await self.session.execute(
            select(Admin).where(Admin.is_active == True).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def remove_admin(self, telegram_id: int) -> bool:
        admin = await self.get_by_telegram_id(telegram_id)
        if admin:
            admin.is_active = False
            await self.flush()
            return True
        return False