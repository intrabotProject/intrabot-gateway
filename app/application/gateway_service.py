"""Couche application du gateway : délégation vers ingestion et search."""

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

    Ne contient aucune logique RAG : il valide les entrées, appelle les
    microservices spécialisés et normalise les réponses pour le frontend.
    """

    def __init__(self, ingestion_client: IngestionClient, search_client: SearchClient) -> None:
        self._ingestion = ingestion_client
        self._search = search_client

    async def search(self, request: SearchRequest, user_role: UserRole) -> SearchResponse:
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
        allowed = set(get_allowed_categories(user_role))
        documents = await self.list_documents()
        return [doc for doc in documents if doc.category in allowed]

    async def ingest(self) -> IngestResponse:
        result = await self._ingestion.ingest()
        return IngestResponse.model_validate(result)

    async def list_documents(self) -> list[DocumentSummary]:
        result = await self._ingestion.list_documents()
        return [DocumentSummary.model_validate(item) for item in result]

    async def collection_stats(self) -> CollectionStats:
        result = await self._ingestion.collection_stats()
        return CollectionStats.model_validate(result)

    async def upload_document(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        category: str = "public",
    ) -> DocumentSummary:
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
        result = await self._ingestion.update_document_category(source, category)
        return DocumentSummary.model_validate(result)

    async def delete_document(self, source: str) -> DeleteDocumentResponse:
        result = await self._ingestion.delete_document(source)
        return DeleteDocumentResponse.model_validate(result)

    async def reindex_document(self, source: str) -> ReindexDocumentResponse:
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
        result = await self._ingestion.submit_document(
            filename, content, content_type, category, submitted_by
        )
        return StagingDocumentSummary.model_validate(result)

    async def list_staging(self) -> list[StagingDocumentSummary]:
        result = await self._ingestion.list_staging()
        return [StagingDocumentSummary.model_validate(item) for item in result]

    async def count_staging(self) -> StagingCountResponse:
        result = await self._ingestion.count_staging()
        return StagingCountResponse.model_validate(result)

    async def approve_staging(self, source: str) -> DocumentSummary:
        result = await self._ingestion.approve_staging(source)
        return DocumentSummary.model_validate(result)

    async def reject_staging(self, source: str) -> RejectStagingResponse:
        result = await self._ingestion.reject_staging(source)
        return RejectStagingResponse.model_validate(result)

    async def health(self) -> HealthResponse:
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
        try:
            await probe()
            return "ok"
        except (httpx.HTTPError, DownstreamError):
            return "error"
