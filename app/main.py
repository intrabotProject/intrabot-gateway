from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings

app = FastAPI(
    title="IntraBot Gateway",
    description=(
        "Orchestrateur API pour la plateforme RAG IntraBot. "
        "Point d'entrée unique entre le frontend et les microservices "
        "d'ingestion et de recherche."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
