from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "billing-platform"
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/billing_platform"
    redis_url: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()
