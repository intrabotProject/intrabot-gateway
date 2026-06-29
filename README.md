# IntraBot Gateway

Orchestrateur API pour la plateforme RAG **IntraBot**. Ce microservice agit comme point d'entrée unique (BFF) entre le frontend et les services downstream d'ingestion et de recherche sémantique.

## Architecture

```
[Frontend :3000]
       │
       ▼
[Gateway :8000]  ← ce repo
       │
       ├──► intrabot-ingestion :8001  (POST /ingest)
       └──► intrabot-search :8002     (POST /api/v1/search)
```

Le gateway ne réimplémente pas la logique RAG (embeddings, ChromaDB, LLM). Il route et agrège les appels vers les microservices spécialisés.

## Endpoints

| Endpoint | Méthode | Description |
|---|---|---|
| `/health` | GET | Santé agrégée (gateway + ingestion + search) |
| `/api/v1/search` | POST | Interroger le pipeline RAG |
| `/api/chat` | POST | Alias vers `/api/v1/search` |
| `/ingest` | POST | Déclencher l'ingestion des documents |

### Administration (`X-API-Key` requis)

| Endpoint | Méthode | Description |
|---|---|---|
| `/admin/documents` | GET | Lister le corpus |
| `/admin/documents/upload` | POST | Uploader un document |
| `/admin/documents/{source}` | DELETE | Supprimer un document |
| `/admin/documents/{source}/reindex` | POST | Réindexer un document |
| `/admin/collection/stats` | GET | Statistiques de la collection |
| `/admin/ingest` | POST | Lancer l'ingestion batch |

### Exemple — recherche RAG

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"question": "Quelle est la politique de télétravail ?", "top_k": 5}'
```

### Exemple — ingestion

```bash
curl -X POST http://localhost:8000/ingest
```

## Démarrage rapide

**1. Prérequis**

Les services downstream doivent être démarrés :

```bash
# Terminal 1 — ingestion (:8001)
cd ../intrabot-ingestion
python -m uvicorn app.infrastructure.api:app --port 8001 --reload

# Terminal 2 — search (:8002)
cd ../intrabot-search/intrabot-search-hexagonal
python -m uvicorn app.main:app --port 8002 --reload
```

**2. Installer et lancer le gateway**

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --port 8000 --reload
```

Swagger : http://127.0.0.1:8000/docs

## Configuration

| Variable | Défaut | Description |
|---|---|---|
| `APP_PORT` | `8000` | Port d'écoute |
| `INGESTION_SERVICE_URL` | `http://localhost:8001` | URL du service d'ingestion |
| `SEARCH_SERVICE_URL` | `http://localhost:8002` | URL du service de recherche |
| `HTTP_TIMEOUT` | `60` | Timeout HTTP vers les services (secondes) |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Origines autorisées pour le frontend (JSON array) |
| `ADMIN_API_KEY` | `dev-admin-key` | Clé pour les routes `/admin/*` (header `X-API-Key`) |

## Intégration frontend

Le frontend appelle directement le gateway :

```env
NEXT_PUBLIC_GATEWAY_URL=http://localhost:8000
```

Le middleware CORS autorise les requêtes depuis `http://localhost:3000` par défaut.

## Structure

```
app/
├── main.py                          ← FastAPI app, CORS
├── core/config.py                   ← Settings (.env)
├── domain/models.py                 ← Contrats Pydantic API
├── application/gateway_service.py   ← Délégation vers les microservices
├── infrastructure/clients.py        ← Clients HTTP (ingestion, search)
└── api/
    ├── routes.py                    ← Chat, search, ingest, health
    ├── admin_routes.py              ← Proxy admin vers ingestion
    ├── auth.py                      ← Vérification X-API-Key
    └── deps.py                      ← Injection de dépendances
```
