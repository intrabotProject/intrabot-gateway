"""Routes d'administration — proxy vers ingestion, protégées par JWT admin ou X-API-Key."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.api.auth import require_admin_access
from app.application.auth_service import AuthService
from app.api.deps import get_gateway_service
from app.application.feedback_service import FeedbackService
from app.application.gateway_service import GatewayService
from app.application.user_admin_service import UserAdminError, UserAdminService
from app.domain.models import (
    AdminUserListItem,
    CollectionStats,
    DeleteDocumentResponse,
    DocumentSummary,
    FeedbackStatsResponse,
    IngestResponse,
    ReindexDocumentResponse,
    RejectStagingResponse,
    StagingCountResponse,
    StagingDocumentSummary,
    UpdateUserRoleBody,
    UserResponse,
)
from app.infrastructure.clients import DownstreamError
from app.infrastructure.database import get_db
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_access)])

_admin_bearer = HTTPBearer(auto_error=False)


def get_user_admin_service(db: Session = Depends(get_db)) -> UserAdminService:
    return UserAdminService(db)


def get_feedback_service(db: Session = Depends(get_db)) -> FeedbackService:
    return FeedbackService(db)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


async def _resolve_actor_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_admin_bearer),
    auth_service: AuthService = Depends(get_auth_service),
) -> str | None:
    if not credentials:
        return None
    try:
        payload = AuthService.decode_access_token(credentials.credentials)
        return str(payload.get("sub")) if payload.get("sub") else None
    except JWTError:
        return None


class UpdateDocumentCategoryBody(BaseModel):
    category: str


def _downstream_http_error(exc: DownstreamError) -> HTTPException:
    status_code = 404 if exc.status_code == 404 else 502
    return HTTPException(status_code=status_code, detail=str(exc))


@router.get("/documents", response_model=list[DocumentSummary])
async def list_documents(
    service: GatewayService = Depends(get_gateway_service),
) -> list[DocumentSummary]:
    try:
        return await service.list_documents()
    except DownstreamError as exc:
        raise _downstream_http_error(exc) from exc


@router.post("/documents/upload", response_model=DocumentSummary)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="public"),
    service: GatewayService = Depends(get_gateway_service),
) -> DocumentSummary:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    try:
        content = await file.read()
        return await service.upload_document(
            filename=file.filename,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            category=category,
        )
    except DownstreamError as exc:
        raise _downstream_http_error(exc) from exc


@router.patch("/documents/{source}/category", response_model=DocumentSummary)
async def update_document_category(
    source: str,
    body: UpdateDocumentCategoryBody,
    service: GatewayService = Depends(get_gateway_service),
) -> DocumentSummary:
    try:
        return await service.update_document_category(source, body.category)
    except DownstreamError as exc:
        raise _downstream_http_error(exc) from exc


@router.delete("/documents/{source}", response_model=DeleteDocumentResponse)
async def delete_document(
    source: str,
    service: GatewayService = Depends(get_gateway_service),
) -> DeleteDocumentResponse:
    try:
        return await service.delete_document(source)
    except DownstreamError as exc:
        raise _downstream_http_error(exc) from exc


@router.post("/documents/{source}/reindex", response_model=ReindexDocumentResponse)
async def reindex_document(
    source: str,
    service: GatewayService = Depends(get_gateway_service),
) -> ReindexDocumentResponse:
    try:
        return await service.reindex_document(source)
    except DownstreamError as exc:
        raise _downstream_http_error(exc) from exc


@router.get("/collection/stats", response_model=CollectionStats)
async def collection_stats(
    service: GatewayService = Depends(get_gateway_service),
) -> CollectionStats:
    try:
        return await service.collection_stats()
    except DownstreamError as exc:
        raise _downstream_http_error(exc) from exc


@router.post("/ingest", response_model=IngestResponse)
async def admin_ingest(
    service: GatewayService = Depends(get_gateway_service),
) -> IngestResponse:
    try:
        return await service.ingest()
    except DownstreamError as exc:
        raise _downstream_http_error(exc) from exc


@router.get("/users", response_model=list[AdminUserListItem])
async def list_users(
    user_admin: UserAdminService = Depends(get_user_admin_service),
) -> list[AdminUserListItem]:
    return [
        AdminUserListItem(
            id=user.id,
            email=user.email,
            role=user.role,
            created_at=user.created_at.isoformat(),
        )
        for user in user_admin.list_users()
    ]


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    body: UpdateUserRoleBody,
    actor_id: str | None = Depends(_resolve_actor_id),
    user_admin: UserAdminService = Depends(get_user_admin_service),
) -> UserResponse:
    try:
        user = user_admin.update_role(user_id, body.role, actor_id)
    except UserAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UserResponse(id=user.id, email=user.email, role=user.role)


@router.get("/staging", response_model=list[StagingDocumentSummary])
async def list_staging(
    service: GatewayService = Depends(get_gateway_service),
) -> list[StagingDocumentSummary]:
    try:
        return await service.list_staging()
    except DownstreamError as exc:
        raise _downstream_http_error(exc) from exc


@router.get("/staging/count", response_model=StagingCountResponse)
async def count_staging(
    service: GatewayService = Depends(get_gateway_service),
) -> StagingCountResponse:
    try:
        return await service.count_staging()
    except DownstreamError as exc:
        raise _downstream_http_error(exc) from exc


@router.post("/staging/{source}/approve", response_model=DocumentSummary)
async def approve_staging(
    source: str,
    service: GatewayService = Depends(get_gateway_service),
) -> DocumentSummary:
    try:
        return await service.approve_staging(source)
    except DownstreamError as exc:
        raise _downstream_http_error(exc) from exc


@router.delete("/staging/{source}", response_model=RejectStagingResponse)
async def reject_staging(
    source: str,
    service: GatewayService = Depends(get_gateway_service),
) -> RejectStagingResponse:
    try:
        return await service.reject_staging(source)
    except DownstreamError as exc:
        raise _downstream_http_error(exc) from exc


@router.get("/feedback/stats", response_model=FeedbackStatsResponse)
async def feedback_stats(
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackStatsResponse:
    total, positive, negative, recent_rows = feedback_service.stats()
    return FeedbackStatsResponse(
        total=total,
        positive=positive,
        negative=negative,
        recent=[
            {
                "id": row.id,
                "user_id": row.user_id,
                "message_id": row.message_id,
                "value": row.value,
                "question": row.question,
                "created_at": row.created_at.isoformat(),
            }
            for row in recent_rows
        ],
    )
