from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_port: int = 8000
    ingestion_service_url: str = "http://localhost:8001"
    search_service_url: str = "http://localhost:8002"
    http_timeout: float = 60.0
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
