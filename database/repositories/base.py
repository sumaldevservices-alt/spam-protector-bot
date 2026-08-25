from typing import TypeVar, Generic, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, update
from sqlalchemy.orm import DeclarativeBase

T = TypeVar("T", bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id_: Any) -> Optional[T]:
        return await self.session.get(self.model, id_)

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def exists(self, **filters) -> bool:
        result = await self.session.execute(
            select(func.count()).select_from(self.model).filter_by(**filters)
        )
        return result.scalar_one() > 0

    async def add(self, instance: T) -> T:
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def commit(self) -> None:
        await self.session.commit()

    async def flush(self) -> None:
        await self.session.flush()

    async def delete(self, instance: T) -> None:
        await self.session.delete(instance)
        await self.session.flush()

    async def execute_raw(self, stmt) -> Any:
        return await self.session.execute(stmt)