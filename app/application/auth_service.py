"""
Inscription, connexion et émission de jetons JWT.

Flux
----
1. register / login → validation → UserRepository → JWT (HS256)
2. get_current_user (auth.py) → decode_access_token → recharge user en base

Bootstrap admin
---------------
Au 1er démarrage, ensure_bootstrap_admin crée un compte admin si l'e-mail
configuré (BOOTSTRAP_ADMIN_*) n'existe pas encore.
"""

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
    """Erreur métier d'authentification (e-mail, mot de passe, rôle)."""


class AuthService:
    """Gère l'inscription, la connexion et les jetons JWT."""

    def __init__(self, db: Session) -> None:
        self._users = UserRepository(db)

    def register(self, email: str, password: str, role: str) -> UserRecord:
        """
        Crée un compte utilisateur.

        Règles : e-mail valide, mot de passe ≥ 8 car., rôle dans REGISTERABLE_ROLES
        (employee, engineer, manager, rh — pas admin).
        """
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
        """Authentifie un utilisateur par e-mail et mot de passe (bcrypt)."""
        user = self._users.get_by_email(email)
        if not user or not pwd_context.verify(password, user.password_hash):
            raise AuthError("E-mail ou mot de passe incorrect.")
        return user

    def get_user(self, user_id: str) -> UserRecord | None:
        """Retourne un utilisateur par son identifiant, ou None s'il n'existe pas."""
        return self._users.get_by_id(user_id)

    def ensure_bootstrap_admin(self) -> None:
        """Crée le compte admin initial au premier démarrage s'il n'existe pas encore."""
        email = settings.bootstrap_admin_email.strip().lower()
        if self._users.get_by_email(email):
            return

        password_hash = pwd_context.hash(settings.bootstrap_admin_password)
        self._users.create(email, password_hash, "admin")

    @staticmethod
    def create_access_token(user: UserRecord) -> str:
        """
        Génère un JWT signé.

        Claims : sub (user id), email, role, exp (JWT_EXPIRE_MINUTES).
        """
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
        """Décode et valide un JWT ; lève JWTError si invalide ou expiré."""
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
