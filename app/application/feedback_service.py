"""Enregistrement et consultation des retours chat."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.infrastructure.feedback_repository import FeedbackRecord, FeedbackRepository


class FeedbackService:
    def __init__(self, db: Session) -> None:
        self._feedback = FeedbackRepository(db)

    def submit(
        self,
        user_id: str,
        message_id: str,
        value: str,
        question: str | None,
        answer: str | None,
    ) -> FeedbackRecord:
        if value not in ("up", "down"):
            raise ValueError("Valeur de feedback invalide.")
        return self._feedback.upsert(user_id, message_id, value, question, answer)

    def stats(self, limit: int = 20) -> tuple[int, int, int, list[FeedbackRecord]]:
        return self._feedback.stats(limit=limit)
