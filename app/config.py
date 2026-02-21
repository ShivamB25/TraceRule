from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/tracerule"
    )
    anthropic_api_key: str = ""
    scan_interval_minutes: int = 5

    model_config = {"env_file": ".env"}


settings = Settings()
