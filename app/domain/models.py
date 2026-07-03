"""
Contrats Pydantic exposés par l'API gateway.

Alignés sur les schémas des microservices ingestion et search.
Utilisés pour la validation des requêtes/réponses et la documentation Swagger.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class DocumentListItem(BaseModel):
    """Document indexé, version simplifiée pour GET /api/v1/documents."""

    source: str
    chunk_count: int
    status: Literal["indexed", "pending"]
    category: str = "public"


class SearchRequest(BaseModel):
    """Corps de requête pour POST /api/v1/search et POST /api/chat."""

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
    """Segment source cité dans une réponse RAG."""

    chunk_id: str
    filename: str
    excerpt: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class SearchResponse(BaseModel):
    """Réponse RAG : réponse LLM, sources et latence."""

    answer: str
    sources: list[SourceChunk]
    excluded_by_threshold: list[SourceChunk] = Field(default_factory=list)
    latency_ms: int = Field(..., ge=0)


class IngestResponse(BaseModel):
    """Résultat d'une ingestion batch (POST /ingest, POST /admin/ingest)."""

    status: str
    files_processed: Optional[int] = None
    chunks_indexed: Optional[int] = None
    total_in_collection: Optional[int] = None


class HealthResponse(BaseModel):
    """Santé agrégée du gateway et des services aval (GET /health)."""

    status: str
    gateway: str = "ok"
    ingestion: Optional[str] = None
    search: Optional[str] = None


class DocumentSummary(BaseModel):
    """Métadonnées complètes d'un document (routes admin)."""

    source: str
    chunk_count: int
    status: Literal["indexed", "pending"]
    category: str = "public"
    file_size_bytes: Optional[int] = None


class CollectionStats(BaseModel):
    """Statistiques de la collection ChromaDB (GET /admin/collection/stats)."""

    collection_name: str
    document_count: int
    chunk_count: int
    indexed_document_count: int
    pending_document_count: int


class DeleteDocumentResponse(BaseModel):
    """Résultat de suppression d'un document (DELETE /admin/documents/{source})."""

    source: str
    file_deleted: bool
    chunks_deleted: int


class ReindexDocumentResponse(BaseModel):
    """Résultat de réindexation (POST /admin/documents/{source}/reindex)."""

    source: str
    chunks_indexed: int
    total_in_collection: int


class AccessCategoryInfo(BaseModel):
    """Catégorie documentaire avec libellé (GET /api/v1/access)."""

    id: str
    label: str


class AccessRoleInfo(BaseModel):
    """Rôle utilisateur avec catégories autorisées (GET /api/v1/access)."""

    id: str
    label: str
    categories: list[str]


class AccessPolicyResponse(BaseModel):
    """Politique d'accès complète rôles / catégories (GET /api/v1/access)."""

    roles: list[AccessRoleInfo]
    categories: list[AccessCategoryInfo]


class RegisterRequest(BaseModel):
    """Corps d'inscription (POST /auth/register). Rôle parmi REGISTERABLE_ROLES."""

    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="employee")


class LoginRequest(BaseModel):
    """Corps de connexion (POST /auth/login)."""

    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    """Profil utilisateur (GET /auth/me, réponses admin)."""

    id: str
    email: str
    role: str


class TokenResponse(BaseModel):
    """JWT et profil utilisateur (POST /auth/register, /auth/login)."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AdminUserListItem(BaseModel):
    """Utilisateur dans la liste admin (GET /admin/users)."""

    id: str
    email: str
    role: str
    created_at: str


class UpdateUserRoleBody(BaseModel):
    """Corps pour modifier le rôle (PATCH /admin/users/{user_id}/role)."""

    role: str


class SubmitFeedbackBody(BaseModel):
    """Retour utilisateur sur une réponse chat (POST /api/v1/feedback)."""

    message_id: str = Field(..., min_length=1, max_length=64)
    value: Literal["up", "down"]
    question: Optional[str] = Field(default=None, max_length=2000)
    answer: Optional[str] = Field(default=None, max_length=8000)


class FeedbackStatsResponse(BaseModel):
    """Statistiques des retours (GET /admin/feedback/stats)."""

    total: int
    positive: int
    negative: int
    recent: list[dict]


class StagingDocumentSummary(BaseModel):
    """Document en attente de validation admin."""

    source: str
    submitted_by: str
    submitted_at: str
    category: str
    file_size_bytes: Optional[int] = None


class StagingCountResponse(BaseModel):
    """Nombre de documents en staging (GET /admin/staging/count)."""

    count: int


class RejectStagingResponse(BaseModel):
    """Confirmation de rejet d'un document staging."""

    source: str
    rejected: bool


class UsageStatsResponse(BaseModel):
    """Statistiques d'usage plateforme (GET /api/v1/stats/usage)."""

    total_users: int
    total_feedback: int
    positive_feedback: int
    negative_feedback: int
    satisfaction_rate: float
    users_by_role: dict[str, int]
