"""
Configuration du gateway chargée depuis les variables d'environnement.

Fichier source : ``.env`` (voir ``.env.example`` à la racine du projet).

Variables principales
---------------------
APP_PORT                  Port d'écoute local (défaut 8000)
INGESTION_SERVICE_URL       URL base du service ingestion (défaut http://localhost:8001)
SEARCH_SERVICE_URL          URL base du service search (défaut http://localhost:8002)
HTTP_TIMEOUT                Timeout HTTP vers les services aval (secondes)
CORS_ORIGINS                Origines CORS autorisées (tableau JSON)
ADMIN_API_KEY               Clé pour les routes /admin/* (header X-API-Key)
DATABASE_URL                Connexion SQLAlchemy (défaut sqlite:///./data/users.db)
JWT_SECRET                  Secret de signature JWT
JWT_ALGORITHM               Algorithme JWT (défaut HS256)
JWT_EXPIRE_MINUTES          Durée de validité du token (défaut 10080 = 7 jours)
BOOTSTRAP_ADMIN_EMAIL       E-mail admin créé au 1er démarrage
BOOTSTRAP_ADMIN_PASSWORD    Mot de passe admin initial
"""

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
