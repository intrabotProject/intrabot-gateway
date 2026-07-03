# IntraBot Gateway

Orchestrateur API (BFF — *Backend For Frontend*) pour la plateforme RAG **IntraBot**.

Ce microservice est le **point d'entrée unique** entre le frontend et les services spécialisés d'ingestion et de recherche. Il ne réimplémente pas la logique RAG (embeddings, ChromaDB, LLM) : il **route**, **sécurise** et **agrège** les appels.

## Architecture

```
[Frontend :3000]
       │
       ▼
[Gateway :8000]  ← ce repo
       │
       ├──► intrabot-ingestion :8001   ingest, admin documents, staging
       ├──► intrabot-search :8002      POST /api/v1/search
       └──► SQLite (users.db)          utilisateurs, feedback
```

### Rôles du gateway

| Responsabilité | Détail |
|---|---|
| **Proxy** | Délègue ingestion et recherche aux microservices downstream |
| **Authentification** | JWT (inscription, connexion, sessions) |
| **Contrôle d'accès** | Filtre documents et recherche selon le rôle utilisateur |
| **CORS** | Autorise le frontend sans modifier les autres services |
| **Données locales** | Utilisateurs, feedback, statistiques d'usage (SQLite) |
| **Santé agrégée** | `/health` vérifie gateway + ingestion + search |

### Ce que le gateway ne fait pas

- Parsing de documents (Docling)
- Embeddings et stockage vectoriel (Cohere, ChromaDB)
- Génération de réponses LLM

Ces responsabilités restent dans `intrabot-ingestion` et `intrabot-search`.

## Politique d'accès

Les documents sont classés par **catégorie** ; chaque **rôle** n'accède qu'à un sous-ensemble :

| Rôle | Catégories accessibles |
|---|---|
| `employee` | `public` |
| `engineer` | `public`, `engineering` |
| `manager` | `public`, `engineering`, `gouvernance` |
| `rh` | `public`, `rh` |
| `admin` | toutes |

Lors d'une recherche, le gateway transmet `allowed_categories` au service search. La liste des documents (`/api/v1/documents`) est filtrée côté gateway selon le même principe.

La politique complète est exposée via `GET /api/v1/access`.

## Authentification

### JWT (utilisateurs et admin UI)

La plupart des routes RAG exigent un header :

```
Authorization: Bearer <access_token>
```

Obtenir un token :

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "votre-mot-de-passe"}'
```

Au premier démarrage, un compte admin est créé automatiquement si absent (voir `BOOTSTRAP_ADMIN_*` dans `.env`).

### Accès admin (`/admin/*`)

Deux méthodes acceptées :

1. **JWT** d'un utilisateur avec le rôle `admin`
2. **Clé API** via le header `X-API-Key` (scripts, dev, CI)

```
X-API-Key: dev-admin-key
```

## Endpoints

### Ops

| Endpoint | Méthode | Auth | Description |
|---|---|---|---|
| `/health` | GET | — | Santé agrégée (gateway + ingestion + search) |

### Authentification

| Endpoint | Méthode | Auth | Description |
|---|---|---|---|
| `/auth/register` | POST | — | Créer un compte |
| `/auth/login` | POST | — | Se connecter (retourne un JWT) |
| `/auth/me` | GET | JWT | Profil de l'utilisateur connecté |

### RAG & chat

| Endpoint | Méthode | Auth | Description |
|---|---|---|---|
| `/api/v1/access` | GET | — | Politique rôles / catégories |
| `/api/v1/documents` | GET | JWT | Documents indexés accessibles au rôle |
| `/api/v1/search` | POST | JWT | Interroger le pipeline RAG |
| `/api/chat` | POST | JWT | Alias vers `/api/v1/search` |
| `/api/v1/feedback` | POST | JWT | Enregistrer un retour (👍 / 👎) sur une réponse |
| `/ingest` | POST | — | Déclencher l'ingestion batch (proxy vers ingestion) |

### Statistiques

| Endpoint | Méthode | Auth | Description |
|---|---|---|---|
| `/api/v1/stats/usage` | GET | JWT | Statistiques d'usage (détail par rôle si admin) |

### Utilisateur

| Endpoint | Méthode | Auth | Description |
|---|---|---|---|
| `/user/documents/submit` | POST | JWT | Soumettre un document en staging (validation admin) |

### Administration

Toutes les routes `/admin/*` requièrent un JWT admin **ou** `X-API-Key`.

| Endpoint | Méthode | Description |
|---|---|---|
| `/admin/documents` | GET | Lister tout le corpus |
| `/admin/documents/upload` | POST | Uploader et indexer un document |
| `/admin/documents/{source}/category` | PATCH | Modifier la catégorie d'un document |
| `/admin/documents/{source}` | DELETE | Supprimer un document |
| `/admin/documents/{source}/reindex` | POST | Réindexer un document |
| `/admin/collection/stats` | GET | Statistiques ChromaDB |
| `/admin/ingest` | POST | Lancer l'ingestion batch |
| `/admin/users` | GET | Lister les utilisateurs |
| `/admin/users/{user_id}/role` | PATCH | Modifier le rôle d'un utilisateur |
| `/admin/staging` | GET | Lister les documents en attente |
| `/admin/staging/count` | GET | Nombre de documents en staging |
| `/admin/staging/{source}/approve` | POST | Approuver et indexer un document |
| `/admin/staging/{source}` | DELETE | Rejeter un document en staging |
| `/admin/feedback/stats` | GET | Statistiques des retours utilisateurs |

## Exemples

### Recherche RAG (authentifié)

```bash
TOKEN="eyJ..."

curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "Quelle est la politique de télétravail ?", "top_k": 5}'
```

Corps de requête (`SearchRequest`) :

| Champ | Type | Défaut | Description |
|---|---|---|---|
| `question` | string | — | Question utilisateur (1–2000 caractères) |
| `top_k` | int | `5` | Nombre de segments à récupérer (1–20) |
| `source_filter` | string? | `null` | Limiter à un document (si accessible au rôle) |
| `min_score` | float | `0.35` | Score de similarité minimum (0–1) |

### Ingestion batch

```bash
curl -X POST http://localhost:8000/ingest
```

### Upload admin

```bash
curl -X POST http://localhost:8000/admin/documents/upload \
  -H "X-API-Key: dev-admin-key" \
  -F "file=@document.pdf" \
  -F "category=public"
```

## Démarrage rapide

### Prérequis

Les services downstream doivent être démarrés :

```bash
# Terminal 1 — ingestion (:8001)
cd ../intrabot-ingestion
python -m uvicorn app.infrastructure.api:app --port 8001 --reload

# Terminal 2 — search (:8002)
cd ../intrabot-search/intrabot-search-hexagonal
python -m uvicorn app.main:app --port 8002 --reload
```

### Installation locale

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # puis adapter les valeurs
python -m uvicorn app.main:app --port 8000 --reload
```

Swagger : http://127.0.0.1:8000/docs

### Docker (stack complète)

Depuis la racine `Projet tnsi/` :

```bash
cp .env.docker.example .env        # renseigner COHERE_API_KEY, JWT_SECRET, etc.
docker compose up -d --build
```

Le gateway est exposé sur le port **8000**.

## Configuration

| Variable | Défaut | Description |
|---|---|---|
| `APP_PORT` | `8000` | Port d'écoute |
| `INGESTION_SERVICE_URL` | `http://localhost:8001` | URL du service d'ingestion |
| `SEARCH_SERVICE_URL` | `http://localhost:8002` | URL du service de recherche |
| `HTTP_TIMEOUT` | `60` | Timeout HTTP vers les services (secondes) |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Origines CORS autorisées (JSON array) |
| `ADMIN_API_KEY` | `dev-admin-key` | Clé pour `/admin/*` (header `X-API-Key`) |
| `DATABASE_URL` | `sqlite:///./data/users.db` | Base SQLite (utilisateurs, feedback) |
| `JWT_SECRET` | `change-me-in-production` | Secret de signature JWT |
| `JWT_ALGORITHM` | `HS256` | Algorithme JWT |
| `JWT_EXPIRE_MINUTES` | `10080` | Durée de validité du token (7 jours) |
| `BOOTSTRAP_ADMIN_EMAIL` | `admin@intrabot.local` | Email admin créé au 1er démarrage |
| `BOOTSTRAP_ADMIN_PASSWORD` | `admin123456` | Mot de passe admin initial |

## Intégration frontend

Le frontend appelle directement le gateway :

```env
NEXT_PUBLIC_GATEWAY_URL=http://localhost:8000
```

Flux typique :

1. `POST /auth/login` → récupérer le JWT
2. Stocker le token côté client
3. Envoyer `Authorization: Bearer <token>` sur `/api/v1/search`, `/api/v1/documents`, etc.

Le middleware CORS autorise `http://localhost:3000` par défaut.

## Structure du projet

> Référence détaillée des fonctions : [docs/FONCTIONS.md](docs/FONCTIONS.md)

```
app/
├── main.py                              ← FastAPI, CORS, lifespan (init DB + admin bootstrap)
├── core/
│   └── config.py                        ← Settings (.env)
├── domain/
│   ├── models.py                        ← Contrats Pydantic API
│   └── access_policy.py                 ← Rôles et catégories documentaires
├── application/
│   ├── gateway_service.py               ← Orchestration (proxy + filtrage par rôle)
│   ├── auth_service.py                  ← JWT, inscription, connexion
│   ├── feedback_service.py              ← Retours utilisateurs
│   ├── usage_stats_service.py           ← Statistiques plateforme
│   └── user_admin_service.py            ← Gestion des rôles utilisateurs
├── infrastructure/
│   ├── clients.py                       ← Clients HTTP (ingestion, search)
│   ├── database.py                      ← SQLite + SQLAlchemy
│   ├── user_repository.py
│   └── feedback_repository.py
└── api/
    ├── routes.py                        ← RAG, ingest, health, feedback, stats
    ├── auth_routes.py                   ← /auth/register, /auth/login, /auth/me
    ├── admin_routes.py                  ← /admin/* (documents, users, staging)
    ├── user_routes.py                   ← /user/documents/submit
    ├── auth.py                          ← JWT, rôles, garde admin
    └── deps.py                          ← Injection de dépendances
```

## Flux — soumission et validation de document

```
Utilisateur                    Gateway                         Ingestion
    │                              │                                │
    │  POST /user/documents/submit │                                │
    │  (JWT + fichier)             │  POST /staging/submit          │
    │ ────────────────────────────►│ ──────────────────────────────►│
    │                              │                                │
    │                              │  GET /admin/staging            │
    │                              │ ◄──────────────────────────────│
    │                              │                                │
    │                              │  POST /staging/{source}/approve│
    │                              │ ──────────────────────────────►│
    │                              │         (indexation)           │
```
