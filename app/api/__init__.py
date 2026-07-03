"""
Couche API — routes HTTP exposées au frontend.

Modules :
    routes.py        RAG, health, feedback, stats, ingest
    auth_routes.py   /auth/register, /auth/login, /auth/me
    admin_routes.py  /admin/* (documents, users, staging)
    user_routes.py   /user/documents/submit
    auth.py          JWT, rôles, garde admin (X-API-Key ou JWT admin)
    deps.py          Injection de dépendances FastAPI
"""
