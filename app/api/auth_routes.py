"""
Inscription, connexion et profil utilisateur.

Routes
------
POST /auth/register  Crée un compte, retourne JWT + profil
POST /auth/login     Authentifie, retourne JWT + profil
GET  /auth/me        Profil de l'utilisateur connecté (JWT requis)
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import AuthenticatedUser, get_auth_service, get_current_user
from app.application.auth_service import AuthError, AuthService
from app.domain.models import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_user_response(user) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, role=user.role)


@router.post("/register", response_model=TokenResponse, summary="Créer un compte")
async def register(
    body: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Inscription : e-mail, mot de passe (≥ 8 car.), rôle (hors admin). Retourne un JWT."""
    try:
        user = auth_service.register(body.email, body.password, body.role)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    token = auth_service.create_access_token(user)
    return TokenResponse(access_token=token, user=_to_user_response(user))


@router.post("/login", response_model=TokenResponse, summary="Se connecter")
async def login(
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Connexion par e-mail / mot de passe. Retourne un JWT."""
    try:
        user = auth_service.login(body.email, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    token = auth_service.create_access_token(user)
    return TokenResponse(access_token=token, user=_to_user_response(user))


@router.get("/me", response_model=UserResponse, summary="Profil connecté")
async def me(current_user: AuthenticatedUser = Depends(get_current_user)) -> UserResponse:
    """Retourne id, e-mail et rôle de l'utilisateur authentifié."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
    )
