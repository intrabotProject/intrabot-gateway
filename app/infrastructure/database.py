"""
Connexion SQLite et session SQLAlchemy.

Base locale : ``./data/users.db`` (configurable via DATABASE_URL).

Tables créées au démarrage (``init_db``) :
    users            Comptes utilisateurs (auth JWT)
    message_feedback Retours 👍/👎 sur les réponses chat
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Base déclarative SQLAlchemy pour les modèles ORM du gateway."""


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    """Crée les tables SQLite si elles n'existent pas (users, message_feedback)."""
    from app.infrastructure.feedback_repository import FeedbackRecord  # noqa: F401
    from app.infrastructure.user_repository import UserRecord  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI : session SQLAlchemy par requête, fermée automatiquement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
