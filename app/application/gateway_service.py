"""
Couche application du gateway : délégation vers ingestion et search.

GatewayService est l'orchestrateur BFF central. Il ne contient aucune logique RAG :
il enrichit les requêtes (allowed_categories, validation source_filter),
appelle les microservices via IngestionClient / SearchClient,
et normalise les réponses Pydantic pour le frontend.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import httpx

from app.domain.models import (
    CollectionStats,
    DeleteDocumentResponse,
    DocumentSummary,
    HealthResponse,
    IngestResponse,
    ReindexDocumentResponse,
    RejectStagingResponse,
    SearchRequest,
    SearchResponse,
    StagingCountResponse,
    StagingDocumentSummary,
)
from app.domain.access_policy import UserRole, get_allowed_categories
from app.infrastructure.clients import DownstreamError, IngestionClient, SearchClient


class GatewayService:
    """
    Orchestrateur BFF (Backend For Frontend).

    Responsabilités :
    - Proxy transparent vers ingestion (documents, staging, ingest)
    - Proxy vers search avec filtrage par rôle (allowed_categories)
    - Santé agrégée (gateway + ingestion + search)
    """

    def __init__(self, ingestion_client: IngestionClient, search_client: SearchClient) -> None:
        self._ingestion = ingestion_client
        self._search = search_client

    async def search(self, request: SearchRequest, user_role: UserRole) -> SearchResponse:
        """
        Interroge le pipeline RAG en filtrant par catégories autorisées.

        Enrichit le payload avec ``allowed_categories`` selon le rôle.
        Si ``source_filter`` pointe vers un document inaccessible, il est ignoré.
        """
        payload = request.model_dump()
        payload["allowed_categories"] = get_allowed_categories(user_role)

        if request.source_filter:
            accessible = await self.list_documents_for_role(user_role)
            allowed_sources = {
                doc.source for doc in accessible if doc.status == "indexed"
            }
            if request.source_filter not in allowed_sources:
                payload["source_filter"] = None

        result = await self._search.search(payload)
        return SearchResponse.model_validate(result)

    async def list_documents_for_role(self, user_role: UserRole) -> list[DocumentSummary]:
        """Retourne les documents dont la catégorie est accessible au rôle donné."""
        allowed = set(get_allowed_categories(user_role))
        documents = await self.list_documents()
        return [doc for doc in documents if doc.category in allowed]

    async def ingest(self) -> IngestResponse:
        """Déclenche l'ingestion batch de tous les documents du dossier source."""
        result = await self._ingestion.ingest()
        return IngestResponse.model_validate(result)

    async def list_documents(self) -> list[DocumentSummary]:
        """Liste l'ensemble du corpus (sans filtre de rôle — usage admin)."""
        result = await self._ingestion.list_documents()
        return [DocumentSummary.model_validate(item) for item in result]

    async def collection_stats(self) -> CollectionStats:
        """Retourne les statistiques de la collection ChromaDB."""
        result = await self._ingestion.collection_stats()
        return CollectionStats.model_validate(result)

    async def upload_document(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        category: str = "public",
    ) -> DocumentSummary:
        """Upload et indexe immédiatement un document (route admin)."""
        result = await self._ingestion.upload_document(
            filename,
            content,
            content_type,
            category,
        )
        return DocumentSummary.model_validate(result)

    async def update_document_category(
        self,
        source: str,
        category: str,
    ) -> DocumentSummary:
        """Modifie la catégorie d'un document et le réindexe."""
        result = await self._ingestion.update_document_category(source, category)
        return DocumentSummary.model_validate(result)

    async def delete_document(self, source: str) -> DeleteDocumentResponse:
        """Supprime un document du disque et de ChromaDB."""
        result = await self._ingestion.delete_document(source)
        return DeleteDocumentResponse.model_validate(result)

    async def reindex_document(self, source: str) -> ReindexDocumentResponse:
        """Réindexe un document existant dans ChromaDB."""
        result = await self._ingestion.reindex_document(source)
        return ReindexDocumentResponse.model_validate(result)

    async def submit_document(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        category: str,
        submitted_by: str,
    ) -> StagingDocumentSummary:
        """Soumet un document en zone de staging (validation admin requise)."""
        result = await self._ingestion.submit_document(
            filename, content, content_type, category, submitted_by
        )
        return StagingDocumentSummary.model_validate(result)

    async def list_staging(self) -> list[StagingDocumentSummary]:
        """Liste les documents en attente de validation admin."""
        result = await self._ingestion.list_staging()
        return [StagingDocumentSummary.model_validate(item) for item in result]

    async def count_staging(self) -> StagingCountResponse:
        """Retourne le nombre de documents en staging."""
        result = await self._ingestion.count_staging()
        return StagingCountResponse.model_validate(result)

    async def approve_staging(self, source: str) -> DocumentSummary:
        """Approuve un document en staging et lance son indexation."""
        result = await self._ingestion.approve_staging(source)
        return DocumentSummary.model_validate(result)

    async def reject_staging(self, source: str) -> RejectStagingResponse:
        """Rejette et supprime un document en staging."""
        result = await self._ingestion.reject_staging(source)
        return RejectStagingResponse.model_validate(result)

    async def health(self) -> HealthResponse:
        """
        Vérifie la disponibilité d'ingestion et search.

        Retourne status ``ok`` si les deux services répondent, sinon ``degraded``.
        """
        ingestion_status = await self._probe_service(self._ingestion.health)
        search_status = await self._probe_service(self._search.health)

        overall = "ok" if ingestion_status == "ok" and search_status == "ok" else "degraded"
        return HealthResponse(
            status=overall,
            ingestion=ingestion_status,
            search=search_status,
        )

    @staticmethod
    async def _probe_service(probe: Callable[[], Awaitable[object]]) -> str:
        """Appelle un endpoint /health aval et retourne ``ok`` ou ``error``."""
        try:
            await probe()
            return "ok"
        except (httpx.HTTPError, DownstreamError):
            return "error"
