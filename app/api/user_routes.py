"""
Routes utilisateur — soumission de documents pour validation admin.

Route
-----
POST /user/documents/submit  Soumet un fichier en staging (JWT requis)

La catégorie doit être autorisée pour le rôle (voir access_policy.py).
Flux : submit → staging (ingestion) → admin approve → indexation ChromaDB.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.auth import AuthenticatedUser, get_current_user
from app.api.deps import get_gateway_service
from app.application.gateway_service import GatewayService
from app.domain.access_policy import get_allowed_categories
from app.domain.models import StagingDocumentSummary
from app.infrastructure.clients import DownstreamError

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/documents/submit", response_model=StagingDocumentSummary)
async def submit_document(
    file: UploadFile = File(...),
    category: str = Form(default="public"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: GatewayService = Depends(get_gateway_service),
) -> StagingDocumentSummary:
    """
    Soumet un document pour validation par l'admin.

    multipart/form-data : file (obligatoire), category (défaut public).
    Retourne 403 si la catégorie n'est pas autorisée pour le rôle.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    allowed = get_allowed_categories(current_user.role)
    if category not in allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Votre profil ne permet pas de soumettre dans la catégorie '{category}'.",
        )

    try:
        content = await file.read()
        return await service.submit_document(
            filename=file.filename,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            category=category,
            submitted_by=current_user.email,
        )
    except DownstreamError as exc:
        status_code = 400 if exc.status_code == 400 else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
