"""Persistance des retours utilisateur sur les réponses du chat."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.infrastructure.database import Base


class FeedbackRecord(Base):
    __tablename__ = "message_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    message_id: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[str] = mapped_column(String(8))
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FeedbackRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def upsert(
        self,
        user_id: str,
        message_id: str,
        value: str,
        question: str | None,
        answer: str | None,
    ) -> FeedbackRecord:
        existing = self._db.scalar(
            select(FeedbackRecord).where(
                FeedbackRecord.user_id == user_id,
                FeedbackRecord.message_id == message_id,
            )
        )
        if existing:
            existing.value = value
            existing.question = question
            existing.answer = answer
            self._db.commit()
            self._db.refresh(existing)
            return existing

        record = FeedbackRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            message_id=message_id,
            value=value,
            question=question,
            answer=answer,
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    def stats(self, limit: int = 20) -> tuple[int, int, int, list[FeedbackRecord]]:
        rows = list(
            self._db.scalars(
                select(FeedbackRecord).order_by(FeedbackRecord.created_at.desc())
            )
        )
        positive = sum(1 for row in rows if row.value == "up")
        negative = sum(1 for row in rows if row.value == "down")
        return len(rows), positive, negative, rows[:limit]
