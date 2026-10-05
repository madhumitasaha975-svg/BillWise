from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plan


class PlanRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_code(self, code: str) -> Plan | None:
        result = await self.session.execute(select(Plan).where(Plan.code == code))
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Plan]:
        result = await self.session.execute(
            select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_minor)
        )
        return list(result.scalars())

    async def add(self, plan: Plan) -> Plan:
        self.session.add(plan)
        await self.session.flush()
        return plan
