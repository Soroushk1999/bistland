# Architecture - Scenario 1 (High-traffic Landing)

## Goals
- 100% durability of submissions under heavy load
- Sub-second page load; immediate user feedback on submit
- Polyglot persistence: PostgreSQL for leads, MongoDB for logs
- Horizontal scalability with containers

## Components
- Django (web): serves landing page and `/api/submit`
- Celery + Redis: async queue for durable background processing
- PostgreSQL: persistent storage for leads
- MongoDB: append-only request logs (timestamp, UA, IP, etc.)
- Nginx: reverse proxy and static delivery

## Flow (Submit)
1. Client POSTs `{phone}` to `/api/submit`
2. Server validates phone, throttles by IP
3. Idempotency via Redis `SETNX dedup:phone:{phone}` TTL 24h
   - If exists: return 200 immediately (`duplicate=true`)
4. Enqueue `persist_lead_task(phone, ip, ua)` to Celery (Redis broker)
5. Enqueue `log_request_task(meta)` to MongoDB
6. Respond 202 immediately (no DB wait)

## Durability
- Redis (AOF) retains tasks until acked by worker; retries on failure
- DB writes run in worker processes, isolated from web latency spikes

## Performance
- Landing HTML cached 60s (Django) + static via Nginx
- Minimal synchronous logic on submit; everything heavy is async

## Security
- Input validation (regex) and per-IP rate limiting
- Run behind Nginx; disable DEBUG in production
- CSRF is exempt only for the JSON API endpoint

## Deployment
- Dockerized services: web, worker, beat, redis, postgres, mongo, nginx
- `.env` controls connections; switchable to managed services in prod

## Observability
- `/healthz` endpoint for container/ELB health checks
- MongoDB contains raw request logs for audit/BI



