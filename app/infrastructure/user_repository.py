"""
Persistance des comptes utilisateurs (table ``users``).

Champs : id (UUID), email (unique), password_hash (bcrypt), role, created_at.
Utilisé par AuthService et UserAdminService.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.domain.access_policy import UserRole
from app.infrastructure.database import Base


class UserRecord(Base):
    """Modèle ORM d'un compte utilisateur."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserRepository:
    """Accès CRUD aux utilisateurs en base SQLite."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_email(self, email: str) -> UserRecord | None:
        """Recherche un utilisateur par e-mail (normalisé en minuscules)."""
        normalized = email.strip().lower()
        return self._db.scalar(select(UserRecord).where(UserRecord.email == normalized))

    def get_by_id(self, user_id: str) -> UserRecord | None:
        """Recherche un utilisateur par identifiant UUID."""
        return self._db.get(UserRecord, user_id)

    def create(self, email: str, password_hash: str, role: UserRole) -> UserRecord:
        """Crée un nouvel utilisateur et le persiste."""
        user = UserRecord(
            id=str(uuid.uuid4()),
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role,
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def count(self) -> int:
        """Retourne le nombre total d'utilisateurs."""
        return len(self._db.scalars(select(UserRecord)).all())

    def list_all(self) -> list[UserRecord]:
        """Liste tous les utilisateurs, du plus récent au plus ancien."""
        return list(
            self._db.scalars(select(UserRecord).order_by(UserRecord.created_at.desc()))
        )

    def update_role(self, user_id: str, role: UserRole) -> UserRecord | None:
        """Modifie le rôle d'un utilisateur. Retourne None si introuvable."""
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.role = role
        self._db.commit()
        self._db.refresh(user)
        return user
