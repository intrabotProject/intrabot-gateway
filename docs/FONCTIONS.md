# Documentation des fonctions — IntraBot Gateway

Référence des fonctions et classes du microservice gateway, organisée par couche architecturale.

---

## 1. Couche API (`app/api/`)

Routes HTTP exposées au frontend. Chaque handler délègue à un service applicatif.

### `routes.py` — Routes publiques

| Fonction | Méthode HTTP | Auth | Description |
|---|---|---|---|
| `health` | GET `/health` | — | Santé agrégée gateway + ingestion + search |
| `get_access_policy` | GET `/api/v1/access` | — | Politique rôles et catégories documentaires |
| `list_documents` | GET `/api/v1/documents` | JWT | Documents indexés accessibles au rôle |
| `search` | POST `/api/v1/search` | JWT | Interroge le pipeline RAG |
| `chat` | POST `/api/chat` | JWT | Alias de `search` |
| `ingest` | POST `/ingest` | — | Déclenche l'ingestion batch |
| `usage_stats` | GET `/api/v1/stats/usage` | JWT | Statistiques d'usage (détail rôles si admin) |
| `submit_feedback` | POST `/api/v1/feedback` | JWT | Enregistre un retour 👍/👎 sur une réponse |

### `auth_routes.py` — Authentification

| Fonction | Méthode HTTP | Description |
|---|---|---|
| `register` | POST `/auth/register` | Crée un compte et retourne un JWT |
| `login` | POST `/auth/login` | Authentifie et retourne un JWT |
| `me` | GET `/auth/me` | Profil de l'utilisateur connecté |

### `user_routes.py` — Actions utilisateur

| Fonction | Méthode HTTP | Description |
|---|---|---|
| `submit_document` | POST `/user/documents/submit` | Soumet un fichier en staging (validation admin) |

### `admin_routes.py` — Administration

| Fonction | Méthode HTTP | Description |
|---|---|---|
| `list_documents` | GET `/admin/documents` | Liste tout le corpus |
| `upload_document` | POST `/admin/documents/upload` | Upload et indexation immédiate |
| `update_document_category` | PATCH `/admin/documents/{source}/category` | Change la catégorie et réindexe |
| `delete_document` | DELETE `/admin/documents/{source}` | Supprime disque + ChromaDB |
| `reindex_document` | POST `/admin/documents/{source}/reindex` | Réindexe un document |
| `collection_stats` | GET `/admin/collection/stats` | Statistiques ChromaDB |
| `admin_ingest` | POST `/admin/ingest` | Ingestion batch |
| `list_users` | GET `/admin/users` | Liste les utilisateurs |
| `update_user_role` | PATCH `/admin/users/{user_id}/role` | Modifie le rôle d'un utilisateur |
| `list_staging` | GET `/admin/staging` | Documents en attente |
| `count_staging` | GET `/admin/staging/count` | Nombre de documents en staging |
| `approve_staging` | POST `/admin/staging/{source}/approve` | Approuve et indexe |
| `reject_staging` | DELETE `/admin/staging/{source}` | Rejette un document |
| `feedback_stats` | GET `/admin/feedback/stats` | Statistiques des retours |

### `auth.py` — Garde-fous d'authentification

| Fonction | Type | Description |
|---|---|---|
| `get_current_user` | Dépendance FastAPI | Extrait l'utilisateur depuis le JWT Bearer |
| `get_user_role` | Dépendance FastAPI | Retourne le rôle de l'utilisateur connecté |
| `require_admin_access` | Dépendance FastAPI | Vérifie JWT admin ou `X-API-Key` |
| `require_admin_api_key` | Dépendance FastAPI | Vérifie uniquement `X-API-Key` (legacy) |

### `deps.py` — Injection de dépendances

| Fonction | Description |
|---|---|
| `get_gateway_service` | Instancie `GatewayService` avec les clients HTTP |

---

## 2. Couche Application (`app/application/`)

Logique métier du gateway : orchestration, auth, feedback, stats.

### `GatewayService`

Orchestrateur BFF. Délègue aux microservices sans implémenter le RAG.

| Méthode | Délègue à | Description |
|---|---|---|
| `search` | search | Recherche RAG filtrée par catégories du rôle |
| `list_documents_for_role` | ingestion | Documents filtrés selon le rôle |
| `ingest` | ingestion | Ingestion batch |
| `list_documents` | ingestion | Corpus complet (admin) |
| `collection_stats` | ingestion | Stats ChromaDB |
| `upload_document` | ingestion | Upload + indexation |
| `update_document_category` | ingestion | Changement de catégorie |
| `delete_document` | ingestion | Suppression |
| `reindex_document` | ingestion | Réindexation |
| `submit_document` | ingestion | Soumission en staging |
| `list_staging` | ingestion | Liste staging |
| `count_staging` | ingestion | Compteur staging |
| `approve_staging` | ingestion | Approbation + indexation |
| `reject_staging` | ingestion | Rejet |
| `health` | ingestion + search | Santé agrégée |
| `_probe_service` | — | Sonde un endpoint `/health` aval |

### `AuthService`

| Méthode | Description |
|---|---|
| `register` | Crée un compte (validation e-mail, mot de passe, rôle) |
| `login` | Authentifie par e-mail / mot de passe |
| `get_user` | Récupère un utilisateur par ID |
| `ensure_bootstrap_admin` | Crée l'admin initial au 1er démarrage |
| `create_access_token` | Génère un JWT signé |
| `decode_access_token` | Décode et valide un JWT |

### `FeedbackService`

| Méthode | Description |
|---|---|
| `submit` | Enregistre ou met à jour un retour 👍/👎 |
| `stats` | Retourne total, positifs, négatifs, derniers retours |

### `UsageStatsService`

| Méthode | Description |
|---|---|
| `get_stats` | Agrège users + feedbacks en statistiques plateforme |

### `UserAdminService`

| Méthode | Description |
|---|---|
| `list_users` | Liste tous les utilisateurs |
| `update_role` | Modifie le rôle (interdit sur soi-même) |

---

## 3. Couche Domain (`app/domain/`)

Règles métier et contrats de données, sans dépendance externe.

### `access_policy.py`

| Fonction | Description |
|---|---|
| `normalize_user_role` | Valide et normalise un rôle (`employee`, `admin`…) |
| `get_allowed_categories` | Catégories documentaires accessibles pour un rôle |

Constantes : `ROLE_CATEGORIES`, `DOCUMENT_CATEGORIES`, `CATEGORY_LABELS`, `ROLE_LABELS`.

### `models.py`

Modèles Pydantic (contrats API) :

| Modèle | Usage |
|---|---|
| `SearchRequest` | Corps de requête chat/RAG |
| `SearchResponse` | Réponse RAG (answer + sources) |
| `DocumentSummary` | Métadonnées d'un document |
| `TokenResponse` | JWT + profil utilisateur |
| `UsageStatsResponse` | Statistiques plateforme |
| `StagingDocumentSummary` | Document en attente de validation |
| `FeedbackStatsResponse` | Stats des retours utilisateurs |

---

## 4. Couche Infrastructure (`app/infrastructure/`)

Implémentations techniques : HTTP, base de données.

### `clients.py`

| Classe / Fonction | Description |
|---|---|
| `DownstreamError` | Exception levée si ingestion/search retourne une erreur HTTP |
| `IngestionClient` | Client HTTP vers `:8001` (ingest, admin, staging) |
| `SearchClient` | Client HTTP vers `:8002` (search RAG) |
| `get_ingestion_client` | Fabrique un client ingestion depuis `settings` |
| `get_search_client` | Fabrique un client search depuis `settings` |

### `database.py`

| Fonction | Description |
|---|---|
| `init_db` | Crée les tables SQLite au démarrage |
| `get_db` | Session SQLAlchemy par requête HTTP |

### `user_repository.py` — `UserRepository`

| Méthode | Description |
|---|---|
| `get_by_email` | Recherche par e-mail |
| `get_by_id` | Recherche par ID |
| `create` | Crée un utilisateur |
| `count` | Nombre total d'utilisateurs |
| `list_all` | Liste tous les utilisateurs |
| `update_role` | Modifie le rôle d'un utilisateur |

### `feedback_repository.py` — `FeedbackRepository`

| Méthode | Description |
|---|---|
| `upsert` | Crée ou met à jour un feedback |
| `stats` | Compte total/positif/négatif + derniers retours |

---

## 5. Configuration (`app/core/config.py`)

| Classe | Description |
|---|---|
| `Settings` | Charge toutes les variables depuis `.env` |
| `settings` | Instance singleton utilisée dans tout le projet |

Variables principales : `ingestion_service_url`, `search_service_url`, `jwt_secret`, `database_url`, `admin_api_key`, `cors_origins`.

---

## 6. Point d'entrée (`app/main.py`)

| Fonction | Description |
|---|---|
| `lifespan` | Au démarrage : crée le dossier data, init DB, crée l'admin bootstrap |

---

## Flux typique — recherche RAG

```
1. routes.search()              ← reçoit POST /api/v1/search + JWT
2. auth.get_user_role()         ← extrait le rôle depuis le token
3. GatewayService.search()      ← ajoute allowed_categories
4. SearchClient.search()        ← HTTP POST vers search :8002
5. SearchResponse               ← renvoyé au frontend
```

## Flux typique — soumission document

```
1. user_routes.submit_document()     ← JWT + fichier
2. GatewayService.submit_document()  ← proxy vers ingestion
3. IngestionClient → POST /staging/submit
4. admin_routes.approve_staging()    ← admin valide
5. GatewayService.approve_staging()  ← indexation dans ChromaDB
```
