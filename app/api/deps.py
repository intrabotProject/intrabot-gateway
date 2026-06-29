"""Injection de dépendances FastAPI pour le gateway."""

from fastapi import Depends

from app.application.gateway_service import GatewayService
from app.infrastructure.clients import (
    IngestionClient,
    SearchClient,
    get_ingestion_client,
    get_search_client,
)


def get_gateway_service(
    ingestion_client: IngestionClient = Depends(get_ingestion_client),
    search_client: SearchClient = Depends(get_search_client),
) -> GatewayService:
    return GatewayService(ingestion_client, search_client)
