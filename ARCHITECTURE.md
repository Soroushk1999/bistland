# System Architecture - High-Traffic Landing Page

## 📋 Table of Contents
- [Overview](#overview)
- [Design Goals](#design-goals)
- [System Architecture](#system-architecture)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Data Models](#data-models)
- [Scalability Strategy](#scalability-strategy)
- [Performance Optimizations](#performance-optimizations)
- [Reliability & Durability](#reliability--durability)
- [Security Architecture](#security-architecture)
- [Monitoring & Observability](#monitoring--observability)
- [Trade-offs & Design Decisions](#trade-offs--design-decisions)
- [Future Improvements](#future-improvements)

## Overview

This system is designed to handle a high-traffic landing page with phone number submission capabilities. The architecture prioritizes **data durability**, **low latency**, and **horizontal scalability** while maintaining operational simplicity.

**Key Characteristics**:
- Async-first design for sub-second response times
- Polyglot persistence for optimal data handling
- Queue-based architecture for 100% durability
- Containerized microservices for easy scaling
- Observable by default with metrics and logging

## Design Goals

### Primary Goals

| Goal | Requirement | Implementation |
|------|-------------|----------------|
| **Durability** | 100% data persistence under load | Redis-backed Celery with AOF persistence |
| **Low Latency** | Sub-second page load and API response | Async processing, caching, CDN-ready |
| **Scalability** | Handle 10K+ concurrent users | Stateless web tier, horizontal scaling |
| **Availability** | 99.9% uptime | Health checks, graceful degradation |
| **Observability** | Real-time insights into system health | Prometheus metrics, structured logging |

### Non-Functional Requirements

- **Security**: Input validation, rate limiting, HTTPS support
- **Maintainability**: Clean code structure, comprehensive documentation
- **Cost Efficiency**: Optimized resource usage, caching strategies
- **Developer Experience**: Easy local setup, clear API contracts

## System Architecture

### High-Level Architecture

```
                                    ┌─────────────────┐
                                    │   External      │
                                    │   Clients       │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │   CloudFlare    │
                                    │   (CDN/WAF)     │
                                    └────────┬────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                         Application Tier                            │
│                                                                     │
│  ┌──────────┐          ┌──────────┐          ┌──────────┐        │
│  │  Nginx   │─────────▶│  Django  │─────────▶│  Django  │        │
│  │  (LB)    │          │  Web 1   │          │  Web 2   │        │
│  └──────────┘          └──────────┘          └──────────┘        │
│                               │                      │             │
└───────────────────────────────┼──────────────────────┼─────────────┘
                                │                      │
                   ┌────────────┴──────────────┬───────┴─────────┐
                   ▼                           ▼                 ▼
          ┌─────────────────┐        ┌─────────────────┐  ┌───────────┐
          │  Redis Cluster  │        │  MinIO Cluster  │  │Prometheus │
          │  (Cache/Queue)  │        │ (Object Store)  │  │ (Metrics) │
          └────────┬────────┘        └─────────────────┘  └───────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────────────────┐
│                         Worker Tier                                 │
│                                                                     │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐ │
│  │ Celery   │     │ Celery   │     │ Celery   │     │ Celery   │ │
│  │ Worker 1 │     │ Worker 2 │     │ Worker 3 │     │ Worker 4 │ │
│  └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘ │
│       │                │                │                │        │
└───────┼────────────────┼────────────────┼────────────────┼────────┘
        │                │                │                │
        └────────────────┴────────────────┴────────────────┘
                                │
                   ┌────────────┴────────────┐
                   ▼                         ▼
          ┌─────────────────┐      ┌─────────────────┐
          │   PostgreSQL    │      │    MongoDB      │
          │   (Primary DB)  │      │  (Audit Logs)   │
          └─────────────────┘      └─────────────────┘
```

### Component Interaction

```
┌──────────┐
│  Client  │
└─────┬────┘
      │ 1. POST /api/submit
      ▼
┌──────────────┐
│    Nginx     │
└──────┬───────┘
       │ 2. Proxy to Django
       ▼
┌──────────────────┐
│  Django Web      │
│                  │
│  1. Validate     │────────┐
│  2. Check Cache  │◀───────┤
│  3. Enqueue Task │        │ Redis
│  4. Return 202   │────────┤ (Cache/Queue)
└──────────────────┘        └─────┬───────┘
       │                          │
       │ 3. Response              │ 4. Task Published
       ▼                          ▼
┌──────────┐              ┌────────────────┐
│  Client  │              │ Celery Worker  │
└──────────┘              │                │
                          │ 5. Process     │
                          │ 6. Save to DB  │
                          └───┬────────┬───┘
                              │        │
                    7. Insert │        │ 7. Log Request
                              ▼        ▼
                      ┌──────────┐  ┌──────────┐
                      │PostgreSQL│  │ MongoDB  │
                      └──────────┘  └──────────┘
```

## Component Details

### 1. Nginx (Reverse Proxy / Load Balancer)

**Role**: Entry point for all HTTP traffic

**Responsibilities**:
- SSL/TLS termination
- Static file serving
- Request routing to Django instances
- Load balancing across multiple web workers
- Rate limiting (first line of defense)
- Compression (gzip/brotli)

**Configuration Highlights**:
```nginx
# nginx.conf
upstream django {
    least_conn;  # Connection-based load balancing
    server web:8000;
    # Add more instances: server web2:8000;
}

location /static/ {
    expires 7d;
    add_header Cache-Control "public, immutable";
}

location / {
    proxy_pass http://django;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

**Scaling**: Deploy behind cloud load balancer (ALB/NLB) for multi-AZ redundancy

---

### 2. Django Web Application

**Role**: HTTP request handler and business logic coordinator

**Architecture Pattern**: Stateless microservice
- No session state (except in Redis)
- Horizontally scalable
- 12-factor app compliant

**Key Modules**:

```
landing/
├── apis/
│   ├── landing_apis.py      # Landing page view (cached)
│   └── submit_phone_apis.py # Phone submission endpoint
├── models/
│   └── Phone.py             # ORM model for leads
├── tasks.py                 # Celery task definitions
├── serializers/             # Request/response validation
├── throttles.py             # Rate limiting logic
└── metrics.py               # Prometheus instrumentation
```

**Request Processing**:
1. **Validation**: DRF serializers validate phone format
2. **Deduplication**: Redis `SETNX` with 24h TTL
3. **Task Enqueue**: Fire-and-forget to Celery
4. **Immediate Response**: 202 Accepted (no DB wait)

**Caching Strategy**:
- Landing page: 60s cache (Django cache framework)
- Static assets: CDN + browser cache (7 days)
- API responses: No caching (real-time deduplication check)

---

### 3. Celery + Redis (Task Queue)

**Role**: Asynchronous task processing and message broker

**Why Celery?**
- Proven at scale (used by Instagram, Robinhood)
- Retry logic and error handling
- Task prioritization support
- Monitoring integration (Flower, Prometheus)

**Why Redis as Broker?**
- In-memory speed for task delivery
- Pub/Sub support for real-time tasks
- Persistence (AOF) for durability
- Doubles as application cache

**Task Types**:

| Task | Priority | Execution | Retry |
|------|----------|-----------|-------|
| `save_phone_in_sql_task` | High | ~50ms | 3x with exponential backoff |
| `log_request_in_mongo_task` | Low | ~20ms | No retry (best-effort) |

**Configuration**:
```python
# celery.py
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"
CELERY_TASK_TIME_LIMIT = 30      # Hard kill after 30s
CELERY_TASK_SOFT_TIME_LIMIT = 20 # Warning at 20s
CELERY_ACKS_LATE = True          # Acknowledge after success
CELERY_TASK_REJECT_ON_WORKER_LOST = True
```

**Durability Guarantees**:
- Redis AOF persistence (append-only file)
- Tasks persisted before acknowledgment
- Worker retries on failure
- Dead letter queue for poisoned messages

---

### 4. PostgreSQL (Primary Database)

**Role**: Persistent storage for phone leads

**Schema Design**:

```sql
CREATE TABLE landing_phone (
    id BIGSERIAL PRIMARY KEY,
    phone VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_phone ON landing_phone(phone);
CREATE INDEX idx_created_at ON landing_phone(created_at);
CREATE INDEX idx_phone_created ON landing_phone(phone, created_at);
```

**Why PostgreSQL?**
- ACID compliance (critical for financial/lead data)
- Mature replication (streaming, logical)
- Advanced indexing (B-tree, GiST, GIN)
- JSON support for schema evolution

**Performance Tuning**:
```sql
-- Connection pooling (PgBouncer in production)
max_connections = 200

-- Memory settings
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 64MB

-- Write optimization
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

**Backup Strategy**:
- Continuous archiving (WAL shipping)
- Daily full backups
- Point-in-time recovery (PITR)
- Cross-region replicas (production)

---

### 5. MongoDB (Audit Log Database)

**Role**: Append-only request logging

**Why MongoDB for Logs?**
- Schema-less (flexible log structure)
- High write throughput (no transactions needed)
- Time-series optimized collections
- Horizontal scaling via sharding

**Document Structure**:
```json
{
  "_id": ObjectId("..."),
  "phone": "09121234567",
  "ip": "192.168.1.100",
  "ua": "Mozilla/5.0...",
  "path": "/api/submit",
  "duplicate": false,
  "ts": ISODate("2025-11-09T12:34:56Z")
}
```

**Indexes**:
```javascript
db.requests.createIndex({ "ts": -1 });        // Recent logs
db.requests.createIndex({ "phone": 1 });      // User lookup
db.requests.createIndex({ "ip": 1, "ts": -1 }); // IP analysis
```

**Retention Policy**:
- TTL index: Auto-delete logs older than 90 days
- Aggregate old data to cold storage (S3)
- Production: Consider MongoDB Atlas with auto-archiving

---

### 6. MinIO (Object Storage)

**Role**: Media file storage (images, videos)

**Why MinIO?**
- S3-compatible API (easy migration to AWS S3)
- Self-hosted (cost control)
- High-performance (written in Go)
- Multi-tenant support

**Use Cases**:
- Landing page hero images
- Product videos
- User-uploaded content (future)
- Static asset backups

**Configuration**:
```python
# Django settings
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_S3_ENDPOINT_URL = "http://minio:9000"
AWS_STORAGE_BUCKET_NAME = "landing-media"
```

**Production Migration**:
Replace MinIO with AWS S3, CloudFlare R2, or Google Cloud Storage:
```python
AWS_S3_ENDPOINT_URL = None  # Use real S3
AWS_STORAGE_BUCKET_NAME = "prod-landing-media"
AWS_S3_CUSTOM_DOMAIN = "cdn.yourdomain.com"  # CloudFront
```

---

### 7. Prometheus + Grafana (Observability)

**Role**: Metrics collection and visualization

**Metrics Collected**:

| Metric | Type | Description |
|--------|------|-------------|
| `endpoint_requests_total` | Counter | Total API requests by status |
| `endpoint_request_duration_seconds` | Histogram | Request latency distribution |
| `django_db_query_duration_seconds` | Histogram | Database query performance |
| `celery_task_runtime_seconds` | Histogram | Task execution time |
| `redis_connected_clients` | Gauge | Active Redis connections |

**Alerting Rules** (example):
```yaml
# prometheus/alerts.yml
groups:
  - name: landing_page
    rules:
      - alert: HighErrorRate
        expr: rate(endpoint_requests_total{status="error"}[5m]) > 0.05
        annotations:
          summary: "Error rate above 5%"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(endpoint_request_duration_seconds_bucket[5m])) > 2
        annotations:
          summary: "P95 latency above 2s"
```

**Grafana Dashboards**:
- **Overview**: Request rate, error rate, latency
- **Database**: Query count, connection pool, slow queries
- **Workers**: Task queue depth, worker utilization
- **Infrastructure**: CPU, memory, disk I/O

---

## Data Flow

### Phone Submission Flow (Detailed)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Submission Flow                              │
└─────────────────────────────────────────────────────────────────────┘

1. Client Request
   └─▶ POST /api/submit {"phone": "09121234567"}
       Headers: Content-Type: application/json
       IP: 192.168.1.100
       User-Agent: Mozilla/5.0...

2. Nginx Layer
   ├─▶ SSL Termination
   ├─▶ Rate Limit Check (100 req/min per IP)
   ├─▶ Add X-Forwarded-For header
   └─▶ Proxy to Django

3. Django View Layer (SubmitPhoneView)
   ├─▶ Parse JSON body
   ├─▶ Validate with SubmitPhoneSerializer
   │   └─▶ Regex check: ^\+?[0-9]{10,15}$
   │   └─▶ Strip whitespace
   ├─▶ Extract client IP (X-Forwarded-For)
   └─▶ Throttle check (20 req/min per IP) [optional]

4. Deduplication Layer
   ├─▶ Generate key: "dedup:phone:09121234567"
   ├─▶ Redis SETNX with TTL 86400s (24h)
   └─▶ If key exists:
       ├─▶ Return 200 OK {"duplicate": true}
       └─▶ Log to MongoDB (non-blocking)

5. Task Enqueue (New Submission)
   ├─▶ save_phone_in_sql_task.delay(phone="09121234567")
   │   └─▶ Serialized to JSON
   │   └─▶ Published to Redis queue "celery"
   │   └─▶ Task ID returned
   ├─▶ log_request_in_mongo_task.delay({...})
   │   └─▶ Published to Redis queue "celery:logs"
   └─▶ Return 202 Accepted {"ok": true, "queued": true}

6. Response to Client
   └─▶ HTTP 202 Accepted (< 100ms total time)
       Body: {"ok": true, "queued": true, "duplicate": false}

7. Background Processing (Celery Worker)
   ├─▶ Worker pulls task from Redis queue
   ├─▶ Execute save_phone_in_sql_task:
   │   ├─▶ INSERT INTO landing_phone (phone, created_at)
   │   │   VALUES ('09121234567', NOW());
   │   └─▶ Commit transaction
   ├─▶ Acknowledge task completion to Redis
   └─▶ Execute log_request_in_mongo_task:
       ├─▶ db.requests.insertOne({
       │     phone: "09121234567",
       │     ip: "192.168.1.100",
       │     ua: "Mozilla/5.0...",
       │     duplicate: false,
       │     ts: ISODate("2025-11-09T12:34:56Z")
       │   })
       └─▶ No acknowledgment (fire-and-forget)

8. Metrics Recording (Throughout)
   ├─▶ endpoint_requests_total{status="success"}.inc()
   ├─▶ endpoint_request_duration_seconds.observe(0.085)
   └─▶ Prometheus scrapes /metrics every 5s
```

### Landing Page View Flow

```
1. Client Request
   └─▶ GET /

2. Nginx
   ├─▶ Check static cache
   └─▶ Proxy to Django

3. Django LandingPageView
   ├─▶ Cache hit check (key: "landing:page:v1")
   │   └─▶ If exists: return cached HTML (< 5ms)
   ├─▶ Cache miss: render template
   │   ├─▶ Load landing.html
   │   ├─▶ Inject context: media_url, minio_enabled
   │   └─▶ Cache for 60 seconds
   └─▶ Return HTML

4. Browser Rendering
   ├─▶ Parse HTML
   ├─▶ Request static assets (CSS, JS)
   │   └─▶ Nginx serves from /static/ (cached 7 days)
   ├─▶ Request hero image
   │   └─▶ MinIO serves from /landing-media/hero-image.jpg
   └─▶ Render page (< 500ms total)
```

## Data Models

### PostgreSQL Schema

```python
# landing/models/Phone.py
class Phone(models.Model):
    phone = models.CharField(max_length=20, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["phone", "created_at"]),
        ]
        db_table = "landing_phone"
```

**Rationale**:
- **Simple schema**: Only essential fields (YAGNI principle)
- **Composite index**: Efficient for duplicate checks and time-range queries
- **No foreign keys**: Reduces complexity for high-write workload
- **Future-proof**: Easy to add fields without migration locks

### MongoDB Schema

```javascript
{
  "_id": ObjectId("673fc4d5e8b9a12345678901"),
  "phone": "09121234567",
  "path": "/api/submit",
  "ip": "192.168.1.100",
  "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
  "duplicate": false,
  "ts": ISODate("2025-11-09T12:34:56.789Z"),
  "meta": {  // Optional: for future extension
    "referrer": "https://google.com",
    "campaign_id": "summer2025",
    "device": "desktop"
  }
}
```

**Indexes**:
- `ts_-1`: Descending time for recent logs
- `phone_1_ts_-1`: User activity timeline
- `ip_1_ts_-1`: IP-based analytics
- TTL index on `ts` (90 days retention)

### Redis Data Structures

```
1. Deduplication Cache
   Key: dedup:phone:{phone_number}
   Type: String
   Value: "1"
   TTL: 86400 seconds (24 hours)
   Example: dedup:phone:09121234567 = "1"

2. Rate Limiting (if enabled)
   Key: throttle:submit_ip:{ip_address}
   Type: String
   Value: Request count
   TTL: 60 seconds
   Example: throttle:submit_ip:192.168.1.100 = "15"

3. Celery Task Queue
   Key: celery
   Type: List (FIFO)
   Value: Serialized task JSON
   Example: {"id": "abc-123", "task": "save_phone_in_sql_task", ...}

4. Page Cache
   Key: views.decorators.cache.cache_page.{url_hash}
   Type: String
   Value: Rendered HTML
   TTL: 60 seconds
```

## Scalability Strategy

### Horizontal Scaling

**Web Tier**:
```bash
# Scale from 3 to 10 instances
docker compose up --scale web=10 -d

# Production: Kubernetes HPA
kubectl autoscale deployment django-web \
  --cpu-percent=70 \
  --min=3 \
  --max=20
```

**Worker Tier**:
```bash
# Scale workers based on queue depth
docker compose up --scale worker=20 -d

# Celery autoscale within container
celery -A config worker --autoscale=10,3
```

### Vertical Scaling Limits

| Component | Max Vertical Scale | Recommended Approach |
|-----------|-------------------|---------------------|
| Django Web | 8 vCPU, 16GB RAM | Scale horizontally instead |
| Celery Worker | 16 vCPU, 32GB RAM | Use multiple smaller workers |
| PostgreSQL | 64 vCPU, 256GB RAM | Read replicas + partitioning |
| Redis | 32GB RAM | Cluster mode (sharding) |

### Database Scaling

**PostgreSQL**:
1. **Read Replicas**: Route analytics queries to replicas
   ```python
   class Phone(models.Model):
       class Meta:
           db_table = "landing_phone"
       
       @classmethod
       def get_stats(cls):
           return cls.objects.using('replica').aggregate(...)
   ```

2. **Partitioning**: By month for historical data
   ```sql
   CREATE TABLE landing_phone_2025_11 PARTITION OF landing_phone
   FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
   ```

3. **Archival**: Move old data to S3/Glacier

**MongoDB**:
- Sharding by phone number hash
- Time-series collections (MongoDB 5.0+)
- Separate cluster for analytics

**Redis**:
- Cluster mode (3 master + 3 replica)
- Separate instances: cache vs. queue vs. rate limiter

### CDN Integration

```
Client ──▶ CloudFlare (Edge Cache)
              │
              ├──▶ Cache Hit: Return (< 50ms)
              │
              └──▶ Cache Miss:
                      │
                      ├──▶ Nginx (Origin)
                      │       │
                      │       └──▶ Django (if dynamic)
                      │
                      └──▶ S3/MinIO (if static)
```

**Cacheable Assets**:
- Static files: CSS, JS, fonts (immutable)
- Media files: Images, videos (versioned URLs)
- Landing page HTML: 60s edge cache

## Performance Optimizations

### 1. Database Query Optimization

**Problem**: N+1 queries in admin panel
```python
# Bad: N+1 queries
for phone in Phone.objects.all():
    print(phone.created_at)  # Additional query per row
```

**Solution**: Select related / prefetch
```python
# Good: Single query with JOIN
phones = Phone.objects.select_related('user').all()
```

### 2. Connection Pooling

**Django Database**:
```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # Keep connections for 10 minutes
    }
}
```

**Production**: Use PgBouncer
```
Django (1000 connections) ──▶ PgBouncer (50 connections) ──▶ PostgreSQL
```

### 3. Caching Strategy

**Multi-Level Cache**:
```
Browser Cache (7 days)
    ↓
CDN Cache (1 hour)
    ↓
Nginx Cache (5 minutes)
    ↓
Django Cache (60 seconds)
    ↓
Database
```

### 4. Async I/O (Future Enhancement)

Current: WSGI (synchronous)
```python
# Blocking I/O
response = requests.get('https://api.example.com')
```

Future: ASGI (asynchronous)
```python
# Non-blocking I/O
async def submit_phone(request):
    async with httpx.AsyncClient() as client:
        response = await client.post('https://api.example.com')
```

**Benefits**:
- 10x more concurrent connections per worker
- Better WebSocket support
- Lower memory footprint

## Reliability & Durability

### Durability Guarantees

**Data Loss Scenarios**:

| Scenario | Impact | Mitigation |
|----------|--------|-----------|
| Redis crash (no persistence) | Lost unprocessed tasks | Enable AOF persistence |
| PostgreSQL crash | Lost uncommitted transactions | WAL archiving + replicas |
| Worker crash mid-task | Task reprocessed | `CELERY_ACKS_LATE = True` |
| Network partition | Delayed processing | Idempotent tasks |
| Full disk | Service degradation | Monitoring + auto-scaling |

### Redis Persistence Configuration

```conf
# redis.conf
appendonly yes
appendfsync everysec       # Balance of speed & safety
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
```

**Recovery Time**:
- AOF replay: ~1 minute per 1GB
- RDB snapshot: ~10 seconds per 1GB

### Celery Task Idempotency

```python
@shared_task(bind=True, max_retries=3)
def save_phone_in_sql_task(self, phone):
    try:
        # Idempotent: get_or_create prevents duplicates
        Phone.objects.get_or_create(phone=phone)
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

### Health Checks

```python
# config/urls.py
class HealthzView(APIView):
    def get(self, request):
        checks = {
            "database": self.check_database(),
            "redis": self.check_redis(),
            "celery": self.check_celery_workers(),
        }
        
        if all(checks.values()):
            return Response({"status": "healthy", **checks})
        else:
            return Response({"status": "degraded", **checks}, status=503)
```

**Kubernetes Probes**:
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /healthz
    port: 8000
  periodSeconds: 5
```

## Security Architecture

### Defense in Depth

```
Layer 1: Network (CloudFlare WAF, DDoS protection)
    ↓
Layer 2: Application (Nginx rate limiting)
    ↓
Layer 3: Framework (Django CSRF, XSS protection)
    ↓
Layer 4: Input Validation (DRF serializers)
    ↓
Layer 5: Database (Parameterized queries)
    ↓
Layer 6: Monitoring (Anomaly detection)
```

### Input Validation

```python
# landing/serializers/phone_submission.py
PHONE_REGEX = re.compile(r"^\+?[0-9]{10,15}$")

class SubmitPhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    
    def validate_phone(self, value: str) -> str:
        value = value.strip()
        if not PHONE_REGEX.match(value):
            raise serializers.ValidationError("invalid_phone")
        # Additional checks
        if value.startswith("00"):  # Block international prefix
            raise serializers.ValidationError("use_plus_prefix")
        return value
```

### Rate Limiting Strategy

**Multiple Layers**:

1. **Nginx** (burst protection):
   ```nginx
   limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
   limit_req zone=api burst=20 nodelay;
   ```

2. **Django** (per-endpoint):
   ```python
   throttle_classes = [SubmitPerIPThrottle]
   # Configured: 20 requests/minute per IP
   ```

3. **CloudFlare** (production):
   - Rate limiting rules
   - Bot detection
   - CAPTCHA challenges

### Sensitive Data Handling

**Phone Number Security**:
- No encryption at rest (not PII in most jurisdictions)
- HTTPS in transit
- Access logging for audit
- GDPR compliance: deletion endpoint (future)

**Environment Secrets**:
```bash
# Never commit .env to git
echo ".env" >> .gitignore

# Use secret management in production
# AWS: Secrets Manager, Parameter Store
# K8s: Sealed Secrets, External Secrets Operator
# Vault: HashiCorp Vault
```

**SQL Injection Prevention**:
```python
# Django ORM uses parameterized queries automatically
Phone.objects.filter(phone=user_input)  # Safe
# Generates: SELECT * FROM phone WHERE phone = %s

# Raw SQL (avoid, but if needed):
Phone.objects.raw("SELECT * FROM phone WHERE phone = %s", [user_input])
```

### CSRF Protection

```python
# settings.py
MIDDLEWARE = [
    'django.middleware.csrf.CsrfViewMiddleware',  # Enabled
]

# API endpoint exemption (uses other auth methods)
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class SubmitPhoneView(APIView):
    # CSRF exempt because:
    # 1. API-only endpoint (no cookies/sessions)
    # 2. Rate limiting provides protection
    # 3. No state-changing actions based on cookies
    pass
```

### HTTPS Enforcement (Production)

```python
# settings.py (production only)
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

## Monitoring & Observability

### Metrics Architecture

```
┌────────────────────────────────────────────────────┐
│                Application Layer                    │
│                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│  │ Django   │    │ Celery   │    │  Redis   │    │
│  │ /metrics │    │ /metrics │    │ Exporter │    │
│  └─────┬────┘    └─────┬────┘    └─────┬────┘    │
└────────┼───────────────┼───────────────┼──────────┘
         │               │               │
         └───────────────┴───────────────┘
                         │
                         ▼ (scrape every 5s)
                ┌─────────────────┐
                │   Prometheus    │
                │   (Time-Series) │
                └────────┬────────┘
                         │
                         ▼ (query)
                ┌─────────────────┐
                │     Grafana     │
                │   (Dashboard)   │
                └─────────────────┘
                         │
                         ▼ (alert)
                ┌─────────────────┐
                │  Alert Manager  │
                │  (PagerDuty)    │
                └─────────────────┘
```

### Key Metrics

**Application Metrics**:
```python
# landing/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request counter
endpoint_requests = Counter(
    'endpoint_requests_total',
    'Total number of requests to the endpoint',
    ['status']  # Labels: success, error, duplicate
)

# Latency histogram
endpoint_latency = Histogram(
    'endpoint_request_duration_seconds',
    'Request duration for the endpoint',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

# Usage in view
def post(self, request):
    start_time = time.perf_counter()
    try:
        # ... process request ...
        endpoint_requests.labels(status="success").inc()
    except Exception as e:
        endpoint_requests.labels(status="error").inc()
    finally:
        duration = time.perf_counter() - start_time
        endpoint_latency.observe(duration)
```

**Infrastructure Metrics** (via Prometheus exporters):
- Node Exporter: CPU, memory, disk, network
- PostgreSQL Exporter: Queries/sec, connection pool, replication lag
- Redis Exporter: Memory usage, hit rate, evictions
- Celery Exporter: Queue depth, task success rate

### Logging Strategy

**Structured Logging**:
```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        }
    },
    'loggers': {
        'landing': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
    }
}
```

**Log Levels**:
- **DEBUG**: Development only (SQL queries, cache hits)
- **INFO**: Request processing, task completion
- **WARNING**: Retry attempts, degraded performance
- **ERROR**: Failed tasks, validation errors
- **CRITICAL**: Service outages, data corruption

**Centralized Logging** (Production):
```
Docker Logs ──▶ Fluentd ──▶ Elasticsearch ──▶ Kibana
                   │
                   └──▶ S3 (archival)
```

### Distributed Tracing (Future)

**OpenTelemetry Integration**:
```python
# Trace a request through multiple services
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def submit_phone(request):
    with tracer.start_as_current_span("submit_phone"):
        # Automatically creates spans for:
        # - HTTP request
        # - Redis operations
        # - Database queries
        # - Celery task dispatch
        pass
```

**Visualization**:
- Jaeger UI: Request flow, bottleneck identification
- Example: Client → Nginx (5ms) → Django (50ms) → Redis (2ms) → Celery (200ms) → PostgreSQL (30ms)

### Alerting Rules

**SLO-Based Alerts**:

```yaml
# prometheus/alerts.yml
groups:
  - name: SLOs
    rules:
      # 99.9% availability target (43 minutes downtime/month)
      - alert: AvailabilityBreach
        expr: |
          (
            sum(rate(endpoint_requests_total{status="success"}[5m]))
            / sum(rate(endpoint_requests_total[5m]))
          ) < 0.999
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Availability below 99.9%"
      
      # 95% of requests under 1 second
      - alert: LatencySLOBreach
        expr: |
          histogram_quantile(0.95,
            rate(endpoint_request_duration_seconds_bucket[5m])
          ) > 1.0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency above 1 second"
      
      # Queue depth (leading indicator)
      - alert: HighQueueDepth
        expr: celery_queue_length > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Celery queue backlog detected"
      
      # Worker health
      - alert: NoWorkersAvailable
        expr: celery_workers_active == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "All Celery workers are down"
```

**Notification Channels**:
- **Critical**: PagerDuty (24/7 on-call)
- **Warning**: Slack #alerts channel
- **Info**: Email digest (daily summary)

## Trade-offs & Design Decisions

### 1. Async Processing vs. Synchronous

**Decision**: Async with Celery

| Aspect | Synchronous | Asynchronous (Chosen) |
|--------|-------------|----------------------|
| Latency | 300ms+ | <100ms |
| Complexity | Low | Medium |
| Durability | Depends on DB | High (queue persistence) |
| Scalability | Limited | Excellent |
| User Experience | Slow under load | Consistent |

**Rationale**: High-traffic scenarios demand immediate feedback. Users don't care about DB write completion, only submission acknowledgment.

### 2. PostgreSQL vs. NoSQL for Leads

**Decision**: PostgreSQL

| Feature | PostgreSQL | MongoDB | DynamoDB |
|---------|-----------|---------|----------|
| ACID | ✅ Full | ⚠️ Limited | ⚠️ Limited |
| Query Flexibility | ✅ SQL | ✅ Rich | ❌ Limited |
| Ops Maturity | ✅ Proven | ✅ Good | ☁️ Managed |
| Cost (self-hosted) | 💰 Low | 💰 Low | 💰💰 High |
| Scalability | ⚠️ Vertical+ | ✅ Horizontal | ✅ Horizontal |

**Rationale**: Lead data requires ACID guarantees for compliance. PostgreSQL offers mature tooling, wide expertise, and sufficient scale for millions of records.

**When to reconsider**: >10M leads with complex sharding needs → Consider CockroachDB or YugabyteDB.

### 3. Redis vs. RabbitMQ for Message Broker

**Decision**: Redis

| Feature | Redis | RabbitMQ |
|---------|-------|----------|
| Latency | 🚀 <1ms | ⚡ ~5ms |
| Durability | ⚠️ AOF (manual) | ✅ Built-in |
| Use Cases | Cache + Queue | Queue only |
| Complexity | Low | Medium |
| Memory Usage | High | Lower |

**Rationale**: Redis serves dual purpose (cache + queue), reducing operational complexity. AOF persistence is sufficient for our durability requirements.

**When to reconsider**: Mission-critical financial transactions → Use RabbitMQ with quorum queues.

### 4. MongoDB vs. PostgreSQL for Logs

**Decision**: MongoDB

| Aspect | MongoDB (Chosen) | PostgreSQL |
|--------|-----------------|------------|
| Write Speed | 🚀 10K+/sec | ⚡ 5K/sec |
| Schema Flexibility | ✅ Schemaless | ❌ Fixed |
| Query Complexity | ⚠️ Aggregation | ✅ SQL |
| Storage Cost | 💰 Lower | 💰💰 Higher |
| TTL Support | ✅ Native | ⚠️ Manual |

**Rationale**: Logs are append-only, don't need transactions, and benefit from flexible schema. MongoDB's TTL indexes auto-delete old data.

**Alternative**: AWS CloudWatch Logs, Elasticsearch (if budget allows).

### 5. MinIO vs. S3

**Decision**: MinIO (dev/staging), S3 (production)

| Feature | MinIO | AWS S3 |
|---------|-------|--------|
| Cost | 💰 Self-hosted | 💰💰 Pay-per-use |
| Performance | 🚀 LAN speed | ⚡ ~50ms |
| Durability | ⚠️ Single-server | ✅ 11 nines |
| Ops Burden | ⚠️ Manual | ✅ Managed |

**Rationale**: MinIO for local development simplicity. S3-compatible API enables seamless production migration.

### 6. Deduplication Window: 24 Hours

**Decision**: 24-hour window in Redis

**Alternative Approaches**:

| Approach | Storage | Accuracy | Cost |
|----------|---------|----------|------|
| DB Unique Constraint | PostgreSQL | 100% | Low |
| Redis TTL (chosen) | Redis | 99.9% | Medium |
| Bloom Filter | Redis | ~95% | Low |

**Rationale**: 
- 24 hours is long enough to catch repeated clicks
- Short enough to allow legitimate resubmissions (typo corrections)
- Redis TTL auto-expires, no cleanup needed
- Edge case: Redis restart = duplicates possible (acceptable trade-off)

**Why not DB constraint?**
- Duplicates are informational, not errors
- We want to log all attempts (even duplicates)
- DB constraint = exception handling overhead

## Future Improvements

### Short-Term (1-3 months)

1. **GraphQL API**: Flexible querying for frontend needs
   ```python
   # landing/schema.py
   import graphene
   
   class PhoneType(DjangoObjectType):
       class Meta:
           model = Phone
   
   class Query(graphene.ObjectType):
       phones = graphene.List(PhoneType)
   ```

2. **Rate Limit Dashboard**: Real-time view of throttled IPs
3. **A/B Testing Framework**: Landing page variant testing
4. **Email Verification**: Send confirmation to submitted phones (via SMS gateway)
5. **Admin Analytics**: Django admin with charts (django-admin-charts)

### Mid-Term (3-6 months)

1. **Kafka Integration**: Event streaming for real-time analytics
   ```
   Django ──▶ Kafka ──▶ Spark Streaming ──▶ Analytics DB
   ```

2. **Machine Learning**: Lead scoring based on submission patterns
   ```python
   # Predict lead quality
   score = ml_model.predict({
       'submission_hour': hour,
       'device': device_type,
       'referrer': referrer_domain
   })
   ```

3. **Multi-Region Deployment**: US-East, EU-West, Asia-Pacific
4. **Circuit Breaker**: Prevent cascade failures
   ```python
   from pybreaker import CircuitBreaker
   
   @CircuitBreaker(fail_max=5, timeout_duration=60)
   def save_to_mongo(data):
       # Fails open if MongoDB is down
       pass
   ```

5. **Feature Flags**: Gradual rollout of new features (LaunchDarkly, Unleash)

### Long-Term (6-12 months)

1. **Event Sourcing**: Audit trail for every state change
   ```
   PhoneSubmitted → PhoneValidated → PhoneStored → EmailSent
   ```

2. **CQRS Pattern**: Separate read/write models
   ```
   Write: PostgreSQL (normalized)
   Read: Elasticsearch (denormalized, fast queries)
   ```

3. **Microservices Architecture**:
   ```
   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
   │   Landing    │    │     Lead     │    │    Email     │
   │   Service    │───▶│   Service    │───▶│   Service    │
   └──────────────┘    └──────────────┘    └──────────────┘
          │                    │                    │
          └────────────────────┴────────────────────┘
                            Event Bus
   ```

4. **AI-Powered Fraud Detection**: Identify fake submissions
5. **Global CDN with Edge Functions**: Cloudflare Workers for API responses
6. **Blockchain Integration**: Immutable lead registry (if compliance requires)

### Technical Debt Items

1. **Upgrade Django**: 5.0 → 5.2 (security patches)
2. **Python 3.11 → 3.12**: Performance improvements (~15% faster)
3. **Add Type Hints**: Gradual typing with mypy
   ```python
   from typing import Dict, Optional
   
   def submit_phone(request: HttpRequest) -> JsonResponse:
       pass
   ```
4. **100% Test Coverage**: Currently ~60%
   ```bash
   pytest --cov=landing --cov-report=html
   coverage report --fail-under=100
   ```
5. **OpenAPI 3.1**: Upgrade drf-spectacular
6. **Database Migrations**: Audit and squash old migrations

## Disaster Recovery

### Backup Strategy

**PostgreSQL**:
```bash
# Automated backups (every 6 hours)
0 */6 * * * pg_dump -h db -U landing landing | gzip > backup_$(date +\%Y\%m\%d_\%H\%M).sql.gz

# Continuous archiving
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://backups/wal/%f'
```

**MongoDB**:
```bash
# Daily snapshot
mongodump --uri="mongodb://mongo:27017/landing_logs" --out=/backups/$(date +\%Y\%m\%d)

# Incremental backups (oplog)
mongodump --uri="mongodb://mongo:27017/local" --collection=oplog.rs
```

**Redis**:
```bash
# RDB snapshot (every 15 minutes)
save 900 1

# AOF for durability
appendonly yes
```

**MinIO/S3**:
- Versioning enabled (30-day retention)
- Cross-region replication
- Lifecycle policies (archive to Glacier after 90 days)

### Recovery Procedures

**Scenario 1: PostgreSQL Failure**
```bash
# 1. Provision new instance
# 2. Restore from latest backup
gunzip -c backup_20250109_1200.sql.gz | psql -h new-db -U landing landing

# 3. Apply WAL segments (PITR to specific timestamp)
# 4. Update connection string in .env
# 5. Restart web/worker services

# Recovery Time Objective (RTO): 15 minutes
# Recovery Point Objective (RPO): 6 hours
```

**Scenario 2: Complete Data Center Failure**
```bash
# 1. Activate standby region (Route53 failover)
# 2. Promote read replica to master
# 3. Scale up workers in new region
# 4. Verify data integrity

# RTO: 30 minutes
# RPO: 5 minutes (replication lag)
```

**Scenario 3: Redis Data Loss**
```bash
# Impact: Lost deduplication cache + task queue
# 1. Restore from latest RDB/AOF
# 2. Accept duplicate submissions for recovery window
# 3. Dedupe in post-processing (SQL query)

# RTO: 5 minutes
# RPO: 15 minutes (last snapshot)
```

### Chaos Engineering

**Automated Failure Testing**:
```yaml
# chaos-mesh.yaml
kind: PodChaos
metadata:
  name: kill-random-worker
spec:
  action: pod-kill
  mode: one
  selector:
    namespaces:
      - landing-prod
    labelSelectors:
      app: celery-worker
  scheduler:
    cron: "0 2 * * *"  # 2 AM daily
```

**Monthly Drills**:
- Week 1: Database failover test
- Week 2: Redis cluster failover
- Week 3: Full region failover
- Week 4: Restore from backup (destructive test in staging)

## Cost Analysis

### Infrastructure Costs (Estimated Monthly)

**Self-Hosted (Docker on EC2)**:
```
EC2 Instances (3x t3.large):        $150
RDS PostgreSQL (db.t3.medium):      $60
ElastiCache Redis (cache.t3.small): $40
S3 Storage (100GB):                 $2.30
Data Transfer:                      $20
CloudWatch Logs:                    $10
Total:                              $282/month
```

**Fully Managed (AWS)**:
```
ECS Fargate (3 tasks):              $100
RDS PostgreSQL (Multi-AZ):          $150
ElastiCache Redis (Cluster):        $120
DocumentDB (MongoDB):               $180
S3 + CloudFront:                    $30
ALB:                                $20
Total:                              $600/month
```

**Kubernetes (EKS)**:
```
EKS Control Plane:                  $75
EC2 Nodes (3x t3.large):            $150
Managed Services (RDS, Redis):      $210
Observability (Datadog):            $150
Total:                              $585/month
```

### Cost Optimization Strategies

1. **Reserved Instances**: 40% savings on compute
2. **Spot Instances**: Celery workers on spot (60% cheaper)
3. **Auto-Scaling**: Scale down during off-peak hours
4. **S3 Lifecycle**: Move old media to Glacier
5. **Compression**: Gzip responses (reduce bandwidth 70%)
6. **CDN**: Reduce origin requests by 80%

**Estimated at Scale** (1M requests/day):
- Basic: $600/month
- High Availability: $1,500/month  
- Global Multi-Region: $3,000/month

## Conclusion

This architecture prioritizes:
1. ✅ **Durability**: No data loss under any load condition
2. ✅ **Performance**: Sub-second response times for excellent UX
3. ✅ **Scalability**: Horizontal scaling for 10K+ concurrent users
4. ✅ **Observability**: Full visibility into system health
5. ✅ **Cost-Efficiency**: Optimal resource utilization

**Production-Ready Checklist**:
- [x] Async processing for non-blocking I/O
- [x] Deduplication to prevent spam
- [x] Polyglot persistence for optimal data handling
- [x] Comprehensive monitoring and alerting
- [x] Security hardening (input validation, rate limiting)
- [x] Disaster recovery procedures documented
- [x] Load testing configuration included
- [x] CI/CD ready (Docker, health checks)

**Key Metrics to Monitor**:
- **Latency**: P95 < 500ms, P99 < 1s
- **Availability**: 99.9% uptime
- **Error Rate**: <0.1% of requests
- **Queue Depth**: <100 pending tasks (normal)
- **Database Connections**: <80% of pool

---

**Document Version**: 1.0  
**Last Updated**: November 9, 2025  
**Author**: Soroushk1999  
**Review Cycle**: Quarterly