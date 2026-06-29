FROM python:3.11-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV APP_PORT=8000 \
    INGESTION_SERVICE_URL=http://ingestion:8001 \
    SEARCH_SERVICE_URL=http://search:8002 \
    HTTP_TIMEOUT=120 \
    ADMIN_API_KEY=dev-admin-key \
    DATABASE_URL=sqlite:////app/data/users.db

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
