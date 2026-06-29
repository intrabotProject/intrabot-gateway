"""Gestion des comptes utilisateurs (admin)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.access_policy import REGISTERABLE_ROLES, UserRole, normalize_user_role
from app.infrastructure.user_repository import UserRecord, UserRepository


class UserAdminError(Exception):
    pass


class UserAdminService:
    def __init__(self, db: Session) -> None:
        self._users = UserRepository(db)

    def list_users(self) -> list[UserRecord]:
        return self._users.list_all()

    def update_role(
        self, user_id: str, role: str, actor_id: str | None
    ) -> UserRecord:
        if actor_id and user_id == actor_id:
            raise UserAdminError("Vous ne pouvez pas modifier votre propre rôle.")

        try:
            normalized_role = normalize_user_role(role)
        except ValueError as exc:
            raise UserAdminError(str(exc)) from exc

        assignable_roles: tuple[UserRole, ...] = (*REGISTERABLE_ROLES, "admin")
        if normalized_role not in assignable_roles:
            raise UserAdminError("Rôle non autorisé.")

        user = self._users.update_role(user_id, normalized_role)
        if not user:
            raise UserAdminError("Utilisateur introuvable.")
        return user
