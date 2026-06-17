import httpx

from app.core.config import settings


class DownstreamError(Exception):
    def __init__(self, service: str, status_code: int, detail: str):
        self.service = service
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{service} returned {status_code}: {detail}")


class IngestionClient:
    def __init__(self, base_url: str, timeout: float):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(f"{self._base_url}/health")
            response.raise_for_status()
            return response.json()

    async def ingest(self) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}/ingest")
            if not response.is_success:
                raise DownstreamError("ingestion", response.status_code, response.text)
            return response.json()


class SearchClient:
    def __init__(self, base_url: str, timeout: float):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(f"{self._base_url}/health")
            response.raise_for_status()
            return response.json()

    async def search(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/v1/search",
                json=payload,
            )
            if not response.is_success:
                raise DownstreamError("search", response.status_code, response.text)
            return response.json()


def get_ingestion_client() -> IngestionClient:
    return IngestionClient(settings.ingestion_service_url, settings.http_timeout)


def get_search_client() -> SearchClient:
    return SearchClient(settings.search_service_url, settings.http_timeout)
