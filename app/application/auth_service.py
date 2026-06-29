"""Inscription, connexion et émission de jetons JWT."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.access_policy import REGISTERABLE_ROLES, UserRole, normalize_user_role
from app.infrastructure.user_repository import UserRecord, UserRepository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, db: Session) -> None:
        self._users = UserRepository(db)

    def register(self, email: str, password: str, role: str) -> UserRecord:
        normalized_email = email.strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise AuthError("Adresse e-mail invalide.")
        if len(password) < 8:
            raise AuthError("Le mot de passe doit contenir au moins 8 caractères.")

        try:
            normalized_role = normalize_user_role(role)
        except ValueError as exc:
            raise AuthError(str(exc)) from exc

        if normalized_role not in REGISTERABLE_ROLES:
            raise AuthError("Ce rôle ne peut pas être choisi à l'inscription.")

        if self._users.get_by_email(normalized_email):
            raise AuthError("Un compte existe déjà avec cette adresse e-mail.")

        password_hash = pwd_context.hash(password)
        return self._users.create(normalized_email, password_hash, normalized_role)

    def login(self, email: str, password: str) -> UserRecord:
        user = self._users.get_by_email(email)
        if not user or not pwd_context.verify(password, user.password_hash):
            raise AuthError("E-mail ou mot de passe incorrect.")
        return user

    def get_user(self, user_id: str) -> UserRecord | None:
        return self._users.get_by_id(user_id)

    def ensure_bootstrap_admin(self) -> None:
        email = settings.bootstrap_admin_email.strip().lower()
        if self._users.get_by_email(email):
            return

        password_hash = pwd_context.hash(settings.bootstrap_admin_password)
        self._users.create(email, password_hash, "admin")

    @staticmethod
    def create_access_token(user: UserRecord) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_expire_minutes
        )
        payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "exp": expire,
        }
        return jwt.encode(
            payload,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

    @staticmethod
    def decode_access_token(token: str) -> dict:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
