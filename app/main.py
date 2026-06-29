"""
Point d'entrée FastAPI du gateway IntraBot.

Le gateway est un BFF : il expose une API unique au frontend, gère le CORS,
protège les routes admin et délègue le travail aux services ingestion et search.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.admin_routes import router as admin_router
from app.api.auth_routes import router as auth_router
from app.application.auth_service import AuthService
from app.core.config import settings
from app.infrastructure.database import SessionLocal, init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db_path = settings.database_url.removeprefix("sqlite:///")
    if db_path and not db_path.startswith(":"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    init_db()
    with SessionLocal() as db:
        AuthService(db).ensure_bootstrap_admin()
    yield


app = FastAPI(
    title="IntraBot Gateway",
    description=(
        "Orchestrateur API pour la plateforme RAG IntraBot. "
        "Point d'entrée unique entre le frontend et les microservices "
        "d'ingestion et de recherche."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(router)
app.include_router(admin_router)
