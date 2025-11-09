# Landing Page (High Traffic) - Scenario 1

## Stack
- Django 5 (web)
- PostgreSQL (RDBMS for leads)
- Redis (broker/cache/idempotency)
- Celery (async worker)
- MongoDB (request logs)
- MinIO (object storage for media files - images/videos)
- Prometheus (metrics collection)
- Nginx (reverse proxy / static)

## Quick start (Docker)

1) Create `.env` next to this file (or copy `.env.example`):
```
DJANGO_DEBUG=1
DB_ENGINE=django.db.backends.postgresql
DB_NAME=landing
DB_USER=landing
DB_PASSWORD=landing
DB_HOST=db
DB_PORT=5432

REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

MONGO_URI=mongodb://mongo:27017
MONGO_DB=landing_logs
MONGO_COLLECTION=requests

CACHE_BACKEND=django_redis.cache.RedisCache
CACHE_LOCATION=redis://redis:6379/1

# MinIO Settings
USE_MINIO=1
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=landing-media
MINIO_USE_HTTPS=0
# Optional: Upload sample media on startup
UPLOAD_SAMPLE_MEDIA=0
```

2) Build & run:
```
docker compose up --build -d
```

**Note:** The entrypoint script automatically:
- Waits for all services (PostgreSQL, Redis, MongoDB, MinIO)
- Runs database migrations
- Collects static files
- Sets up MinIO bucket
- Optionally uploads sample media (if `UPLOAD_SAMPLE_MEDIA=1`)

3) Open:
- App (via Nginx): http://localhost/
- App (direct): http://localhost:8080/
- Health: http://localhost:8080/healthz
- Metrics: http://localhost:8080/metrics/
- API schema: http://localhost:8080/api/schema/
- Swagger UI: http://localhost:8080/api/docs/
- Redoc: http://localhost:8080/api/redoc/
- Admin: http://localhost:8080/admin
- Prometheus UI: http://localhost:9090/

**Note:** Internal services (Redis, PostgreSQL, MongoDB, MinIO) are only accessible within Docker network. To access them from host, uncomment port mappings in `docker-compose.yml`.

**MinIO Console:** Visit http://localhost:9001 (default credentials: minioadmin/minioadmin).

**Prometheus:** Visit http://localhost:9090 to explore collected metrics (scrapes `/metrics/` from the Django service).

**OpenAPI / Swagger:**
- JSON schema: `python manage.py spectacular --file schema/openapi.json`
- YAML schema: `python manage.py spectacular --format yaml --file schema/openapi.yaml`
- Interactive docs: `/api/docs/` (Swagger UI) and `/api/redoc/` (ReDoc)

## Local without Docker (dev)
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## API
- POST `/api/submit` JSON `{ "phone": "0912..." }`
  - 202 Accepted on queue (duplicate=false)
  - 200 OK if duplicate within 24h
  - 400 invalid phone, 429 rate limited

## MinIO / Media Files

Media files (images/videos for landing page) are stored in MinIO. To upload files:

1. Access MinIO console (uncomment port 9001 in docker-compose.yml)
2. Or use the management command:
   ```bash
   docker compose exec web python manage.py upload_sample_media
   ```

The landing page template automatically loads images from MinIO if available, with fallback to external URLs.

## Notes
- **Automatic Setup:** Entrypoint handles migrations, static collection, MinIO bucket setup, and exposes Prometheus metrics automatically
- **Async:** Request enqueues Celery tasks and returns immediately
- **Durability:** Redis broker keeps tasks until processed; DB writes happen in worker
- **Idempotency:** Redis SETNX per phone for 24h
- **Logging:** MongoDB stores `{ip, ua, phone, duplicate, ts}`
- **Caching:** Landing page cached 60s; Nginx serves static
- **Storage:** Media files (images/videos) stored in MinIO object storage
- **Monitoring:** Prometheus scrapes `/metrics/`; integrate with Grafana or alerting as needed
- **Security:** Validation, throttling; run behind Nginx; keep DEBUG=0 in prod



