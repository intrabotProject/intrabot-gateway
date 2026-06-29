"""Configuration du gateway chargée depuis les variables d'environnement."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres d'exécution du BFF IntraBot."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_port: int = 8000
    ingestion_service_url: str = "http://localhost:8001"
    search_service_url: str = "http://localhost:8002"
    http_timeout: float = 60.0
    cors_origins: list[str] = ["http://localhost:3000"]
    admin_api_key: str = "dev-admin-key"
    database_url: str = "sqlite:///./data/users.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    bootstrap_admin_email: str = "admin@intrabot.local"
    bootstrap_admin_password: str = "admin123456"


settings = Settings()
