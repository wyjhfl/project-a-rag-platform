# Release Notes — v1.0.0 Production Landing

## Overview

This release hardens the Project A RAG Platform from RC (Release Candidate) to production-ready status. The focus is on operational reliability, security, and observability rather than new business features.

## Key Changes

### Job External Worker System
- Jobs now support **DB-backed lease worker** mode in addition to the existing in-process daemon thread.
- New job fields: `retry_count`, `max_retries`, `locked_by`, `locked_at`, `heartbeat_at`, `timeout_seconds`, `cancel_requested`.
- New job statuses: `RETRYING`, `CANCELLED` (in addition to `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`).
- New API endpoint: `POST /api/v1/jobs/{job_id}/cancel` with role-based access control.
- External worker: `python -m app.job_worker` with configurable `WORKER_ID`, `JOB_POLL_INTERVAL_SECONDS`, `JOB_DEFAULT_TIMEOUT_SECONDS`.
- Demo mode: `JOB_EXECUTION_MODE=inprocess` (default, backward compatible).
- Production mode: `JOB_EXECUTION_MODE=worker` with Docker worker service.

### Database Migration System
- Lightweight migration runner: `python -m app.migrations status` and `python -m app.migrations upgrade`.
- Migrations are versioned, idempotent, and support both SQLite and PostgreSQL.
- Safe upgrade path from v1.0.0-rc.1 schema.

### Rate Limiting
- In-memory rate limiting middleware with configurable `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS_PER_MINUTE`, `RATE_LIMIT_BURST`.
- Health check endpoints (`/healthz`, `/readyz`, `/health`, `/metrics`) are exempt.
- Rate limit key uses SHA-256 hash of API key (never the raw key) or client IP.
- Returns 429 with `Retry-After` header and standard error format.

### Metrics Endpoint
- `GET /metrics` returns Prometheus text format metrics.
- Metrics: request count, request latency, error count, job status count, job duration, process uptime.
- Configurable via `METRICS_ENABLED` (default: off in demo, on in production).
- No authentication required for scraping (configure network-level access in production).

### Secret Scanning
- `scripts/secret_scan.py` detects leaked API keys, tokens, and passwords.
- Distinguishes placeholders from real secrets.
- Integrated into CI pipeline.

### OpenAPI TypeScript Type Generation
- `scripts/export_openapi.py` exports OpenAPI JSON schema.
- `npm run api:types` generates `frontend/src/api/generated.ts`.
- Ensures frontend types stay in sync with backend API.

### Docker Production Profile
- New `worker` service in `docker-compose.yml` for production job execution.
- Worker shares the same Docker image as the API service.
- Demo compose (`docker-compose.demo.yml`) uses in-process job execution (no worker needed).

### E2E Testing
- 21 Playwright E2E test cases across 8 spec files.
- `scripts/e2e_demo_smoke.ps1` for pre-flight service checks.
- CI e2e-smoke job on `workflow_dispatch` only.

## Configuration Changes

New environment variables:
- `JOB_EXECUTION_MODE` — `inprocess` (demo) or `worker` (production)
- `JOB_POLL_INTERVAL_SECONDS` — Worker poll interval (default: 5)
- `JOB_DEFAULT_TIMEOUT_SECONDS` — Job timeout (default: 300)
- `RATE_LIMIT_ENABLED` — Enable rate limiting (default: false)
- `RATE_LIMIT_REQUESTS_PER_MINUTE` — Rate limit (default: 60)
- `RATE_LIMIT_BURST` — Burst allowance (default: 30)
- `RATE_LIMIT_EXEMPT_PATHS` — Comma-separated exempt paths
- `METRICS_ENABLED` — Enable metrics endpoint (default: false)

## Breaking Changes

- `JobRecord` model now includes additional fields. Existing API consumers should handle unknown fields gracefully.
- No API path changes. All existing endpoints remain backward compatible.

## Upgrade from v1.0.0-rc.1

1. Back up your database: `cp data/app.db data/app.db.backup` (SQLite) or `pg_dump` (PostgreSQL).
2. Pull the new code.
3. Run migrations: `python -m app.migrations upgrade`.
4. Update `.env` with new configuration variables (see `.env.example`).
5. For production: set `JOB_EXECUTION_MODE=worker` and add the worker service to your compose stack.
6. Restart services.
