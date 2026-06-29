"""Agrégation des statistiques d'usage de la plateforme."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.models import UsageStatsResponse
from app.infrastructure.feedback_repository import FeedbackRepository
from app.infrastructure.user_repository import UserRepository


class UsageStatsService:
    """
    Combine les données utilisateurs et feedbacks pour produire
    les statistiques d'usage exposées aux utilisateurs connectés.
    """

    def __init__(self, db: Session) -> None:
        self._users = UserRepository(db)
        self._feedback = FeedbackRepository(db)

    def get_stats(self, include_role_breakdown: bool = False) -> UsageStatsResponse:
        total_users = self._users.count()
        total, positive, negative, _ = self._feedback.stats(limit=0)

        satisfaction_rate = round(positive / total * 100, 1) if total > 0 else 0.0

        users_by_role: dict[str, int] = {}
        if include_role_breakdown:
            for user in self._users.list_all():
                users_by_role[user.role] = users_by_role.get(user.role, 0) + 1

        return UsageStatsResponse(
            total_users=total_users,
            total_feedback=total,
            positive_feedback=positive,
            negative_feedback=negative,
            satisfaction_rate=satisfaction_rate,
            users_by_role=users_by_role,
        )
