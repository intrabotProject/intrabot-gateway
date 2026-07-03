"""
Package racine du microservice IntraBot Gateway.

BFF (Backend For Frontend) en FastAPI qui route, sécurise et agrège les appels
vers intrabot-ingestion (:8001) et intrabot-search (:8002).

Structure :
    api/            Routes HTTP et garde-fous d'authentification
    application/    Logique métier (orchestration, auth, feedback, stats)
    domain/         Contrats Pydantic et politique d'accès documentaire
    infrastructure/ Clients HTTP downstream, SQLite, repositories
    core/           Configuration (.env)
"""
