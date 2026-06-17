from fastapi import APIRouter, Depends, HTTPException

from app.application.gateway_service import GatewayService
from app.domain.models import HealthResponse, IngestResponse, SearchRequest, SearchResponse
from app.infrastructure.clients import (
    DownstreamError,
    get_ingestion_client,
    get_search_client,
    IngestionClient,
    SearchClient,
)

router = APIRouter()


def get_gateway_service(
    ingestion_client: IngestionClient = Depends(get_ingestion_client),
    search_client: SearchClient = Depends(get_search_client),
) -> GatewayService:
    return GatewayService(ingestion_client, search_client)


@router.get("/health", response_model=HealthResponse, tags=["ops"])
async def health(service: GatewayService = Depends(get_gateway_service)) -> HealthResponse:
    result = await service.health()
    if result.status != "ok":
        raise HTTPException(status_code=503, detail=result.model_dump())
    return result


@router.post(
    "/api/v1/search",
    response_model=SearchResponse,
    tags=["rag"],
    summary="Interroger le pipeline RAG",
)
async def search(
    request: SearchRequest,
    service: GatewayService = Depends(get_gateway_service),
) -> SearchResponse:
    try:
        return await service.search(request)
    except DownstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/api/chat",
    response_model=SearchResponse,
    tags=["rag"],
    summary="Alias chat vers le pipeline RAG",
)
async def chat(
    request: SearchRequest,
    service: GatewayService = Depends(get_gateway_service),
) -> SearchResponse:
    try:
        return await service.search(request)
    except DownstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post(
    "/ingest",
    response_model=IngestResponse,
    tags=["ingestion"],
    summary="Déclencher l'ingestion des documents",
)
async def ingest(service: GatewayService = Depends(get_gateway_service)) -> IngestResponse:
    try:
        return await service.ingest()
    except DownstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
