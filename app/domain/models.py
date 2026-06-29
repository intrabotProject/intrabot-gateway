"""Contrats Pydantic exposés par l'API gateway (alignés sur ingestion et search)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class DocumentListItem(BaseModel):
    source: str
    chunk_count: int
    status: Literal["indexed", "pending"]
    category: str = "public"


class SearchRequest(BaseModel):
    """Corps de requête pour le chat / la recherche RAG."""

    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    source_filter: Optional[str] = Field(
        default=None,
        description="Limiter la recherche à un document (nom de fichier).",
    )
    min_score: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Score de similarité minimum pour inclure un segment.",
    )

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
    excluded_by_threshold: list[SourceChunk] = Field(default_factory=list)
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


class DocumentSummary(BaseModel):
    source: str
    chunk_count: int
    status: Literal["indexed", "pending"]
    category: str = "public"
    file_size_bytes: Optional[int] = None


class CollectionStats(BaseModel):
    collection_name: str
    document_count: int
    chunk_count: int
    indexed_document_count: int
    pending_document_count: int


class DeleteDocumentResponse(BaseModel):
    source: str
    file_deleted: bool
    chunks_deleted: int


class ReindexDocumentResponse(BaseModel):
    source: str
    chunks_indexed: int
    total_in_collection: int


class AccessCategoryInfo(BaseModel):
    id: str
    label: str


class AccessRoleInfo(BaseModel):
    id: str
    label: str
    categories: list[str]


class AccessPolicyResponse(BaseModel):
    roles: list[AccessRoleInfo]
    categories: list[AccessCategoryInfo]


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="employee")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AdminUserListItem(BaseModel):
    id: str
    email: str
    role: str
    created_at: str


class UpdateUserRoleBody(BaseModel):
    role: str


class SubmitFeedbackBody(BaseModel):
    message_id: str = Field(..., min_length=1, max_length=64)
    value: Literal["up", "down"]
    question: Optional[str] = Field(default=None, max_length=2000)
    answer: Optional[str] = Field(default=None, max_length=8000)


class FeedbackStatsResponse(BaseModel):
    total: int
    positive: int
    negative: int
    recent: list[dict]
