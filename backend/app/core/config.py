from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """All configuration comes from environment variables / the root .env file."""

    database_url: str = "postgresql+asyncpg://billwise:billwise@localhost:5432/billwise"
    app_env: str = "development"

    # JWT Configuration
    jwt_secret_key: str = "billwise-dev-super-secret-key-change-in-production-min32chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Payment Gateway (Razorpay)
    razorpay_key_id: str = "rzp_test_placeholder"
    razorpay_key_secret: str = "rzp_test_secret_placeholder"
    razorpay_webhook_secret: str = "billwise_webhook_secret_key_12345"
    fake_gateway_mode: bool = True

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


settings = Settings()