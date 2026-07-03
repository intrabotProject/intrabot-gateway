# IntraBot Gateway

Orchestrateur API (BFF) pour la plateforme RAG **IntraBot** — point d'entrée unique entre le frontend et les microservices ingestion/search.

```
[Frontend :3000] → [Gateway :8000] → intrabot-ingestion :8001
                                    → intrabot-search :8002
                                    → SQLite (users, feedback)
```

## Démarrage rapide

**Prérequis** : ingestion (`:8001`) et search (`:8002`) démarrés.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --port 8000 --reload
```

- **Swagger** : http://127.0.0.1:8000/docs
- **Configuration** : voir `.env.example` et `app/core/config.py`
- **Frontend** : `NEXT_PUBLIC_GATEWAY_URL=http://localhost:8000`

### Docker (stack complète)

Depuis la racine `Projet tnsi/` :

```bash
cp .env.docker.example .env
docker compose up -d --build
```

## Documentation

La documentation détaillée (architecture, endpoints, auth, politique d'accès, modèles)
se trouve dans les **docstrings des fichiers Python** sous `app/`.

Elle est également exposée via **Swagger** (`/docs`) grâce aux descriptions des routes FastAPI.
