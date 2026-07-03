"""
Authentification JWT, rôles utilisateur et accès admin.

Dépendances FastAPI
-------------------
get_current_user       Extrait l'utilisateur depuis Authorization: Bearer <token>
get_user_role          Retourne le rôle (pour filtrage documents/recherche)
require_admin_access   JWT admin OU header X-API-Key (routes /admin/*)

JWT payload : sub (user id), email, role, exp.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.application.auth_service import AuthService
from app.core.config import settings
from app.domain.access_policy import UserRole
from app.infrastructure.database import get_db

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    """Utilisateur authentifié extrait du JWT et rechargé depuis SQLite."""

    id: str
    email: str
    role: UserRole


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Dépendance FastAPI : instancie AuthService avec une session DB."""
    return AuthService(db)


def _user_record_to_authenticated(user) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        role=user.role,  # type: ignore[arg-type]
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthenticatedUser:
    """
    Dépendance FastAPI : extrait et valide l'utilisateur depuis le JWT Bearer.

    Lève HTTP 401 si token absent, invalide, expiré ou utilisateur introuvable.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentification requise.")

    try:
        payload = AuthService.decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Jeton invalide.")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Jeton invalide ou expiré.") from exc

    user = auth_service.get_user(str(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable.")

    return _user_record_to_authenticated(user)


async def get_user_role(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> UserRole:
    """Dépendance FastAPI : retourne le rôle de l'utilisateur connecté."""
    return current_user.role


async def require_admin_access(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """
    Garde d'accès admin pour toutes les routes /admin/*.

    Accepte :
    1. JWT d'un utilisateur avec rôle ``admin`` en base
    2. Header X-API-Key égal à ADMIN_API_KEY (scripts, dev, CI)
    """
    if credentials:
        try:
            payload = AuthService.decode_access_token(credentials.credentials)
            user_id = payload.get("sub")
            if user_id:
                user = auth_service.get_user(str(user_id))
                if user and user.role == "admin":
                    return
        except JWTError:
            pass

    if x_api_key and x_api_key == settings.admin_api_key:
        return

    raise HTTPException(status_code=401, detail="Accès administrateur requis.")


async def require_admin_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    """Conservé pour compatibilité — préférer require_admin_access."""
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
