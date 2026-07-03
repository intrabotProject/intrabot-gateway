"""Clients HTTP vers les microservices downstream (ingestion, search)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings


class DownstreamError(Exception):
    """Erreur HTTP renvoyée par ingestion ou search."""

    def __init__(self, service: str, status_code: int, detail: str):
        self.service = service
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{service} returned {status_code}: {detail}")


class _BaseClient:
    """Factorise les appels HTTP GET/POST vers un microservice aval."""

    def __init__(self, service_name: str, base_url: str, timeout: float) -> None:
        self._service_name = service_name
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        raise_on_error: bool = True,
    ) -> httpx.Response:
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.request(
                method,
                url,
                json=json,
                data=data,
                files=files,
            )

        if raise_on_error and not response.is_success:
            raise DownstreamError(self._service_name, response.status_code, response.text)
        return response

    async def _get_json(self, path: str) -> dict[str, Any]:
        response = await self._request("GET", path)
        return response.json()

    async def _post_json(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._request("POST", path, json=json)
        return response.json()

    async def health(self) -> dict[str, Any]:
        response = await self._request("GET", "/health", raise_on_error=False)
        response.raise_for_status()
        return response.json()


class IngestionClient(_BaseClient):
    """Client HTTP vers intrabot-ingestion (:8001)."""

    def __init__(self, base_url: str, timeout: float) -> None:
        super().__init__("ingestion", base_url, timeout)

    async def ingest(self) -> dict[str, Any]:
        return await self._post_json("/ingest")

    async def list_documents(self) -> list[dict[str, Any]]:
        response = await self._request("GET", "/admin/documents")
        return response.json()

    async def collection_stats(self) -> dict[str, Any]:
        return await self._get_json("/admin/collection/stats")

    async def upload_document(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        category: str = "public",
    ) -> dict[str, Any]:
        response = await self._request(
            "POST",
            "/admin/documents/upload",
            files={"file": (filename, content, content_type)},
            data={"category": category},
        )
        return response.json()

    async def update_document_category(
        self,
        source: str,
        category: str,
    ) -> dict[str, Any]:
        encoded_source = quote(source, safe="")
        response = await self._request(
            "PATCH",
            f"/admin/documents/{encoded_source}/category",
            json={"category": category},
        )
        return response.json()

    async def delete_document(self, source: str) -> dict[str, Any]:
        encoded_source = quote(source, safe="")
        response = await self._request("DELETE", f"/admin/documents/{encoded_source}")
        return response.json()

    async def reindex_document(self, source: str) -> dict[str, Any]:
        encoded_source = quote(source, safe="")
        return await self._post_json(f"/admin/documents/{encoded_source}/reindex")

    async def submit_document(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        category: str,
        submitted_by: str,
    ) -> dict[str, Any]:
        response = await self._request(
            "POST",
            "/staging/submit",
            files={"file": (filename, content, content_type)},
            data={"category": category, "submitted_by": submitted_by},
        )
        return response.json()

    async def list_staging(self) -> list[dict[str, Any]]:
        response = await self._request("GET", "/staging")
        return response.json()

    async def count_staging(self) -> dict[str, Any]:
        return await self._get_json("/staging/count")

    async def approve_staging(self, source: str) -> dict[str, Any]:
        encoded_source = quote(source, safe="")
        return await self._post_json(f"/staging/{encoded_source}/approve")

    async def reject_staging(self, source: str) -> dict[str, Any]:
        encoded_source = quote(source, safe="")
        response = await self._request("DELETE", f"/staging/{encoded_source}")
        return response.json()


class SearchClient(_BaseClient):
    """Client HTTP vers intrabot-search (:8002)."""

    def __init__(self, base_url: str, timeout: float) -> None:
        super().__init__("search", base_url, timeout)

    async def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post_json("/api/v1/search", json=payload)


def get_ingestion_client() -> IngestionClient:
    """Fabrique un client ingestion configuré depuis ``settings``."""
    return IngestionClient(settings.ingestion_service_url, settings.http_timeout)


def get_search_client() -> SearchClient:
    """Fabrique un client search configuré depuis ``settings``."""
    return SearchClient(settings.search_service_url, settings.http_timeout)
