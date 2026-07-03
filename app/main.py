"""
Point d'entrée FastAPI du gateway IntraBot.

Rôle
----
BFF (Backend For Frontend) : API unique pour le frontend, CORS, auth JWT,
proxy vers ingestion (:8001) et search (:8002).

Démarrage (lifespan)
--------------------
1. Crée le dossier parent de la base SQLite (``./data/`` par défaut).
2. ``init_db()`` — tables ``users`` et ``message_feedback``.
3. ``AuthService.ensure_bootstrap_admin()`` — compte admin initial si absent.

Routers montés
--------------
- ``auth_router``   → ``/auth/*``
- ``router``        → routes publiques et RAG
- ``admin_router``  → ``/admin/*``
- ``user_router``   → ``/user/*``
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.admin_routes import router as admin_router
from app.api.auth_routes import router as auth_router
from app.api.user_routes import router as user_router
from app.application.auth_service import AuthService
from app.core.config import settings
from app.infrastructure.database import SessionLocal, init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialise la base SQLite et le compte admin bootstrap au démarrage."""
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
app.include_router(user_router)
