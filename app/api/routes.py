"""
Routes publiques du gateway : RAG, santé, feedback, stats, ingestion.

Endpoints
---------
GET  /health              Santé agrégée (gateway + ingestion + search)
GET  /api/v1/access       Politique rôles / catégories (sans auth)
GET  /api/v1/documents    Documents indexés accessibles au rôle (JWT)
POST /api/v1/search       Recherche RAG (JWT)
POST /api/chat            Alias de /api/v1/search (JWT)
POST /api/v1/feedback     Retour 👍/👎 sur une réponse (JWT)
GET  /api/v1/stats/usage  Statistiques plateforme (JWT, détail rôles si admin)
POST /ingest              Ingestion batch (proxy ingestion, sans auth)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import AuthenticatedUser, get_current_user
from app.api.auth import get_user_role
from app.api.deps import get_gateway_service
from app.application.feedback_service import FeedbackService
from app.application.gateway_service import GatewayService
from app.application.usage_stats_service import UsageStatsService
from app.domain.access_policy import (
    CATEGORY_LABELS,
    DOCUMENT_CATEGORIES,
    ROLE_CATEGORIES,
    ROLE_LABELS,
    USER_ROLES,
    UserRole,
)
from app.domain.models import (
    AccessCategoryInfo,
    AccessPolicyResponse,
    AccessRoleInfo,
    DocumentListItem,
    HealthResponse,
    IngestResponse,
    SearchRequest,
    SearchResponse,
    SubmitFeedbackBody,
    UsageStatsResponse,
)
from app.infrastructure.clients import DownstreamError
from app.infrastructure.database import get_db

router = APIRouter()


def get_feedback_service(db: Session = Depends(get_db)) -> FeedbackService:
    return FeedbackService(db)


def get_usage_stats_service(db: Session = Depends(get_db)) -> UsageStatsService:
    return UsageStatsService(db)


async def _handle_downstream_error(coro):
    """Convertit DownstreamError en HTTP 502."""
    try:
        return await coro
    except DownstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/health", response_model=HealthResponse, tags=["ops"])
async def health(service: GatewayService = Depends(get_gateway_service)) -> HealthResponse:
    """
    Santé agrégée : sonde ingestion et search.

    Retourne 200 si tout est ok, 503 si un service est dégradé.
    """
    result = await service.health()
    if result.status != "ok":
        raise HTTPException(status_code=503, detail=result.model_dump())
    return result


@router.get(
    "/api/v1/access",
    response_model=AccessPolicyResponse,
    tags=["rag"],
    summary="Politique d'accès (rôles et catégories)",
)
async def get_access_policy() -> AccessPolicyResponse:
    """Expose la matrice rôles ↔ catégories documentaires (voir access_policy.py)."""
    return AccessPolicyResponse(
        roles=[
            AccessRoleInfo(
                id=role,
                label=ROLE_LABELS[role],
                categories=list(ROLE_CATEGORIES[role]),
            )
            for role in USER_ROLES
        ],
        categories=[
            AccessCategoryInfo(id=category, label=CATEGORY_LABELS[category])
            for category in DOCUMENT_CATEGORIES
        ],
    )


@router.get(
    "/api/v1/documents",
    response_model=list[DocumentListItem],
    tags=["rag"],
    summary="Lister les documents disponibles pour le chat",
)
async def list_documents(
    user_role: UserRole = Depends(get_user_role),
    service: GatewayService = Depends(get_gateway_service),
) -> list[DocumentListItem]:
    """Documents indexés filtrés selon les catégories autorisées pour le rôle."""
    documents = await _handle_downstream_error(service.list_documents_for_role(user_role))
    return [
        DocumentListItem(
            source=doc.source,
            chunk_count=doc.chunk_count,
            status=doc.status,
            category=doc.category,
        )
        for doc in documents
        if doc.status == "indexed"
    ]


@router.post(
    "/api/v1/search",
    response_model=SearchResponse,
    tags=["rag"],
    summary="Interroger le pipeline RAG",
)
async def search(
    request: SearchRequest,
    user_role: UserRole = Depends(get_user_role),
    service: GatewayService = Depends(get_gateway_service),
) -> SearchResponse:
    """
    Recherche RAG : question, top_k, source_filter optionnel, min_score.

    Le gateway ajoute allowed_categories selon le rôle avant d'appeler search.
    """
    return await _handle_downstream_error(service.search(request, user_role))


@router.post(
    "/api/chat",
    response_model=SearchResponse,
    tags=["rag"],
    summary="Alias chat vers le pipeline RAG",
)
async def chat(
    request: SearchRequest,
    user_role: UserRole = Depends(get_user_role),
    service: GatewayService = Depends(get_gateway_service),
) -> SearchResponse:
    """Alias exact de POST /api/v1/search pour compatibilité frontend."""
    return await search(request, user_role, service)


@router.post(
    "/ingest",
    response_model=IngestResponse,
    tags=["ingestion"],
    summary="Déclencher l'ingestion des documents",
)
async def ingest(service: GatewayService = Depends(get_gateway_service)) -> IngestResponse:
    """Proxy vers POST /ingest du service ingestion (batch)."""
    return await _handle_downstream_error(service.ingest())


@router.get(
    "/api/v1/stats/usage",
    response_model=UsageStatsResponse,
    tags=["stats"],
    summary="Statistiques d'usage de la plateforme",
)
async def usage_stats(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: UsageStatsService = Depends(get_usage_stats_service),
) -> UsageStatsResponse:
    """Stats utilisateurs et feedbacks. Répartition par rôle visible uniquement pour admin."""
    return service.get_stats(include_role_breakdown=(current_user.role == "admin"))


@router.post(
    "/api/v1/feedback",
    tags=["rag"],
    summary="Enregistrer un retour sur une réponse",
    status_code=204,
)
async def submit_feedback(
    body: SubmitFeedbackBody,
    current_user: AuthenticatedUser = Depends(get_current_user),
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> None:
    """Enregistre ou met à jour un retour 👍 (up) ou 👎 (down) sur un message chat."""
    feedback_service.submit(
        user_id=current_user.id,
        message_id=body.message_id,
        value=body.value,
        question=body.question,
        answer=body.answer,
    )
