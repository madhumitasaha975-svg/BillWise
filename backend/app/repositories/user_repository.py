from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, User


class UserRepository:
    """All database access for users and their customer profile. No business rules here."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def add(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()  # sends INSERT so user.id is available
        return user

    async def get_customer_by_user_id(self, user_id) -> Customer | None:
        result = await self.session.execute(select(Customer).where(Customer.user_id == user_id))
        return result.scalar_one_or_none()

    async def add_customer(self, customer: Customer) -> Customer:
        self.session.add(customer)
        await self.session.flush()
        return customer
