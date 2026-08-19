from app.database.base import Base
from app.models import *  # noqa: F401,F403
from app.database.session import engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
