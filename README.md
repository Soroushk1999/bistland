# 🚀 High-Traffic Landing Page System

A production-ready Django-based landing page with phone submission handling, designed to process high volumes of traffic with 100% data durability and sub-second response times.

## 📋 Table of Contents
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [API Documentation](#-api-documentation)
- [Monitoring & Observability](#-monitoring--observability)
- [Load Testing](#-load-testing)
- [Development](#-development)
- [Production Deployment](#-production-deployment)
- [License](#-license)

## ✨ Features

- **High Performance**: Async task processing with immediate user feedback
- **100% Durability**: Guaranteed data persistence under heavy load using Redis-backed Celery queues
- **Deduplication**: 24-hour window to prevent duplicate submissions
- **Polyglot Persistence**: PostgreSQL for leads, MongoDB for request logs
- **Object Storage**: MinIO for media files (images/videos)
- **Real-time Monitoring**: Prometheus metrics with Grafana dashboards
- **Load Testing**: Built-in Locust configuration for performance testing
- **Auto-scaling Ready**: Horizontal scalability with containerized services
- **Rate Limiting**: Per-IP throttling to prevent abuse
- **API Documentation**: OpenAPI/Swagger auto-generated docs

## 🏗 Architecture

```
┌─────────┐      ┌────────┐      ┌──────────┐
│ Client  │─────▶│ Nginx  │─────▶│  Django  │
└─────────┘      └────────┘      └──────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
                ┌────────┐        ┌────────┐        ┌────────┐
                │ Redis  │◀───────│ Celery │───────▶│ MinIO  │
                └────────┘        └────────┘        └────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
              ┌──────────┐      ┌──────────┐      ┌───────────┐
              │PostgreSQL│      │ MongoDB  │      │Prometheus │
              └──────────┘      └──────────┘      └───────────┘
```

**Flow**:
1. Client submits phone number to `/api/submit`
2. Django validates input and checks deduplication cache (Redis)
3. Request is queued to Celery for async processing
4. Celery worker saves to PostgreSQL and logs to MongoDB
5. Immediate 202/200 response to client (no DB wait)

## 🛠 Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | Django 5.0 | API & landing page |
| **Web Server** | Gunicorn + Nginx | Production WSGI + reverse proxy |
| **Task Queue** | Celery 5.3 | Async job processing |
| **Message Broker** | Redis 7 | Task queue & caching |
| **Primary Database** | PostgreSQL 15 | Lead storage (ACID) |
| **Logging Database** | MongoDB 6 | Request logs |
| **Object Storage** | MinIO | Media files (S3-compatible) |
| **Monitoring** | Prometheus + Grafana | Metrics & dashboards |
| **Load Testing** | Locust 2.29 | Performance testing |
| **Containerization** | Docker & Compose | Deployment |

## 🚦 Quick Start

### Prerequisites
- Docker & Docker Compose
- 4GB RAM minimum
- Ports available: 80, 3000, 8000, 8089, 9000, 9001, 9090

### 1. Clone & Configure

```bash
git clone <repository-url>
cd landing-page-scenario
```

Create `.env` file:

```env
# Django
DJANGO_DEBUG=1
DJANGO_SECRET_KEY=your-secret-key-change-in-production

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=landing
DB_USER=landing
DB_PASSWORD=landing
DB_HOST=db
DB_PORT=5432

# Redis & Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# MongoDB
MONGO_URI=mongodb://mongo:27017
MONGO_DB=landing_logs
MONGO_COLLECTION=requests

# Cache
CACHE_BACKEND=django_redis.cache.RedisCache
CACHE_LOCATION=redis://redis:6379/1

# MinIO (Object Storage)
USE_MINIO=1
MINIO_ENDPOINT=minio:9000
MINIO_PUBLIC_URL=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=landing-media
MINIO_USE_HTTPS=0

# Optional: Upload sample media on startup
UPLOAD_SAMPLE_MEDIA=0
```

### 2. Launch Services

```bash
docker compose up --build -d
```

**The entrypoint script automatically handles**:
- Service health checks (PostgreSQL, Redis, MongoDB, MinIO)
- Database migrations
- Static file collection
- MinIO bucket creation
- Optional sample media upload

### 3. Access Applications

| Service | URL | Description |
|---------|-----|-------------|
| **Landing Page** | http://localhost | Main application (via Nginx) |
| **API Direct** | http://localhost:8000 | Django server |
| **Health Check** | http://localhost:8000/healthz | Service health |
| **Metrics** | http://localhost:8000/metrics | Prometheus metrics |
| **API Docs (Swagger)** | http://localhost:8000/api/swagger | Interactive API docs |
| **API Docs (ReDoc)** | http://localhost:8000/api/redoc | Alternative API docs |
| **Grafana** | http://localhost:3000 | Dashboards (admin/admin) |
| **Prometheus** | http://localhost:9090 | Metrics explorer |
| **MinIO Console** | http://localhost:9001 | Object storage UI (minioadmin/minioadmin) |
| **Locust** | http://localhost:8089 | Load testing UI |

### 4. Verify Setup

```bash
# Check all services are running
docker compose ps

# View logs
docker compose logs -f web

# Submit a test phone number
curl -X POST http://localhost:8000/api/submit \
  -H "Content-Type: application/json" \
  -d '{"phone": "09121234567"}'
```

## ⚙️ Configuration

### Environment Variables

See `.env.example` for all available options. Key configurations:

**Performance Tuning**:
```env
# Number of Gunicorn workers (formula: 2 * CPU_cores + 1)
# Edit in docker-compose.yml: --workers 3

# Celery concurrency
# Edit in docker-compose.yml: -c 4

# Cache TTL for landing page (seconds)
# In settings.py: CACHE_TTL = 60
```

**Security** (Production):
```env
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOST=yourdomain.com
DJANGO_SECRET_KEY=generate-a-strong-random-key
```

**Rate Limiting**:
Uncomment in `landing/apis/submit_phone_apis.py`:
```python
throttle_classes = [SubmitPerIPThrottle]
```

Configure in `config/settings.py`:
```python
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "submit_ip": "20/min",  # 20 requests per minute per IP
    },
}
```

## 📡 API Documentation

### Submit Phone Number

**Endpoint**: `POST /api/submit`

**Request**:
```json
{
  "phone": "09121234567"
}
```

**Response (Success - New)**:
```json
{
  "ok": true,
  "queued": true,
  "duplicate": false
}
```

**Response (Success - Duplicate)**:
```json
{
  "ok": true,
  "duplicate": true
}
```

**Response (Error - Invalid Phone)**:
```json
{
  "phone": ["invalid_phone"]
}
```

**Phone Format Rules**:
- 10-15 digits
- Optional leading `+`
- Regex: `^\+?[0-9]{10,15}$`

**Interactive Documentation**:
- Visit http://localhost:8000/api/swagger for Swagger UI
- Visit http://localhost:8000/api/redoc for ReDoc

**Export OpenAPI Schema**:
```bash
# JSON format
docker compose exec web python manage.py spectacular --file schema.json

# YAML format
docker compose exec web python manage.py spectacular --format yaml --file schema.yaml
```

## 📊 Monitoring & Observability

### Prometheus Metrics

Access at http://localhost:9090

**Available Metrics**:
- `endpoint_requests_total{status="success|error"}` - Total requests
- `endpoint_request_duration_seconds` - Request latency histogram
- `django_http_requests_total_by_method` - HTTP requests by method
- `django_db_query_duration_seconds` - Database query performance

**Example Queries**:
```promql
# Request rate per second
rate(endpoint_requests_total[1m])

# 95th percentile latency
histogram_quantile(0.95, rate(endpoint_request_duration_seconds_bucket[5m]))

# Success rate
(sum(endpoint_requests_total{status="success"}) / sum(endpoint_requests_total)) * 100
```

### Grafana Dashboards

Access at http://localhost:3000 (admin/admin)

Pre-configured dashboard includes:
- Total requests counter
- Success rate percentage
- Request rate graph (req/s)
- Latency distribution (p50, p95, p99)
- Error breakdown table
- Latency over time graph

**Dashboard Location**: `grafana/dashboards/my_dashboard.json`

### Logs

```bash
# Web server logs
docker compose logs -f web

# Celery worker logs
docker compose logs -f worker

# All services
docker compose logs -f

# MongoDB request logs (requires mongo shell)
docker compose exec mongo mongosh landing_logs --eval "db.requests.find().limit(10)"
```

## 🔥 Load Testing

### Using Locust

Locust is pre-configured and running at http://localhost:8089

**Start a Load Test**:
1. Open http://localhost:8089
2. Set number of users (e.g., 1000)
3. Set spawn rate (e.g., 100 users/second)
4. Host is pre-configured to `http://web:8000`
5. Click "Start swarming"

**Test Scenarios** (`locustfile.py`):
- 80% weight: Submit phone endpoint
- 20% weight: Landing page view

**Command Line Load Test**:
```bash
# Run headless load test
docker compose exec locust-master locust \
  -f /mnt/locust/locustfile.py \
  --host http://web:8000 \
  --users 1000 \
  --spawn-rate 100 \
  --run-time 5m \
  --headless
```

**Scale Workers**:
```bash
# Add more workers for distributed load generation
docker compose up --scale locust-worker=5 -d
```

### Manual Testing

```bash
# Benchmark with Apache Bench
ab -n 10000 -c 100 -p phone.json -T application/json http://localhost:8000/api/submit

# phone.json content:
# {"phone": "09121234567"}
```

## 💻 Development

### Local Setup (Without Docker)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment
export DJANGO_SETTINGS_MODULE=config.settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver 0.0.0.0:8000

# In another terminal, run Celery worker
celery -A config worker -l info

# In another terminal, run Celery beat
celery -A config beat -l info
```

**Note**: You'll need to run Redis, PostgreSQL, MongoDB, and MinIO locally or update settings to use cloud services.

### Running Tests

```bash
# Run Django tests
docker compose exec web python manage.py test

# Run with coverage
docker compose exec web pytest --cov=landing --cov-report=html
```

### Database Management

```bash
# Create migrations
docker compose exec web python manage.py makemigrations

# Apply migrations
docker compose exec web python manage.py migrate

# Access Django shell
docker compose exec web python manage.py shell

# Access PostgreSQL
docker compose exec db psql -U landing -d landing

# Access MongoDB
docker compose exec mongo mongosh landing_logs

# Access Redis CLI
docker compose exec redis redis-cli
```

### MinIO Media Management

```bash
# Upload sample media
docker compose exec web python manage.py upload_sample_media

# Setup MinIO bucket manually
docker compose exec web python manage.py setup_minio
```

## 🌐 Production Deployment

### Pre-Production Checklist

- [ ] Set `DJANGO_DEBUG=0`
- [ ] Generate strong `DJANGO_SECRET_KEY`
- [ ] Configure `DJANGO_ALLOWED_HOST`
- [ ] Use managed databases (RDS, Atlas, ElastiCache)
- [ ] Enable HTTPS (SSL certificates)
- [ ] Configure firewall rules
- [ ] Set up log aggregation (ELK, CloudWatch)
- [ ] Enable rate limiting
- [ ] Configure backups
- [ ] Set up alerting (PagerDuty, Opsgenie)
- [ ] Scale worker pools based on load
- [ ] Use CDN for static files

### Scaling Recommendations

**Horizontal Scaling**:
```bash
# Scale web workers
docker compose up --scale web=5 -d

# Scale Celery workers
docker compose up --scale worker=10 -d
```

**Managed Services** (AWS Example):
- **Web**: ECS/Fargate or EKS
- **Database**: RDS PostgreSQL Multi-AZ
- **Cache/Queue**: ElastiCache Redis Cluster
- **Object Storage**: S3 (replace MinIO)
- **Logs**: DocumentDB or Atlas MongoDB
- **Load Balancer**: ALB with health checks
- **Monitoring**: CloudWatch + Grafana Cloud

### Docker Production Build

```dockerfile
# Use multi-stage build for smaller images
# Disable dev dependencies
# Use gunicorn with proper worker configuration
# See Dockerfile for production settings
```

### Environment-Specific Settings

Create separate env files:
- `.env.development`
- `.env.staging`
- `.env.production`

Load with:
```bash
docker compose --env-file .env.production up -d
```

## 🔒 Security Considerations

1. **Input Validation**: Phone regex prevents SQL injection
2. **Rate Limiting**: Throttle per-IP to prevent abuse
3. **CSRF Protection**: Enabled for web forms
4. **SQL Injection**: Using Django ORM (parameterized queries)
5. **XSS Protection**: Template auto-escaping enabled
6. **HTTPS**: Configure SSL/TLS in production
7. **Secrets Management**: Use environment variables, never commit secrets

**Production Security**:
```python
# In settings.py
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
```

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check service status
docker compose ps

# View specific service logs
docker compose logs web
docker compose logs worker

# Restart services
docker compose restart

# Rebuild from scratch
docker compose down -v
docker compose up --build -d
```

### Database Connection Issues

```bash
# Check if PostgreSQL is ready
docker compose exec db pg_isready -U landing

# Check database exists
docker compose exec db psql -U landing -l

# Reset database (WARNING: destroys data)
docker compose down -v
docker compose up -d db
docker compose exec web python manage.py migrate
```

### Celery Tasks Not Processing

```bash
# Check worker is running
docker compose ps worker

# View worker logs
docker compose logs -f worker

# Check Redis connection
docker compose exec redis redis-cli ping

# Manually trigger task
docker compose exec web python manage.py shell
>>> from landing.tasks import save_phone_in_sql_task
>>> save_phone_in_sql_task.delay("09121234567")
```

### Performance Issues

1. **Check Metrics**: Visit Grafana dashboard
2. **Database Queries**: Enable Django Debug Toolbar in dev
3. **Worker Capacity**: Scale Celery workers
4. **Cache Hit Rate**: Monitor Redis stats
5. **Network**: Check Nginx access logs

## 📚 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [PostgreSQL Best Practices](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Prometheus Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Soroushk1999**

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

---

**Built with ❤️ for high-traffic scenarios**