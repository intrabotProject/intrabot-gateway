from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, raw_question: str) -> str:
        stripped = raw_question.strip()
        if not stripped:
            raise ValueError("question must not be blank or whitespace-only")
        return stripped


class SourceChunk(BaseModel):
    chunk_id: str
    filename: str
    excerpt: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class SearchResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    latency_ms: int = Field(..., ge=0)


class IngestResponse(BaseModel):
    status: str
    files_processed: Optional[int] = None
    chunks_indexed: Optional[int] = None
    total_in_collection: Optional[int] = None


class HealthResponse(BaseModel):
    status: str
    gateway: str = "ok"
    ingestion: Optional[str] = None
    search: Optional[str] = None
