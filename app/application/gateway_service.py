import httpx

from app.domain.models import HealthResponse, IngestResponse, SearchRequest, SearchResponse
from app.infrastructure.clients import DownstreamError, IngestionClient, SearchClient


class GatewayService:
    def __init__(self, ingestion_client: IngestionClient, search_client: SearchClient):
        self._ingestion = ingestion_client
        self._search = search_client

    async def search(self, request: SearchRequest) -> SearchResponse:
        payload = request.model_dump()
        result = await self._search.search(payload)
        return SearchResponse.model_validate(result)

    async def ingest(self) -> IngestResponse:
        result = await self._ingestion.ingest()
        return IngestResponse.model_validate(result)

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
    async def _probe_service(probe) -> str:
        try:
            await probe()
            return "ok"
        except (httpx.HTTPError, DownstreamError):
            return "error"
