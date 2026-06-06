# Final Production Acceptance Checklist

This checklist is the authoritative v1.0.2 production gate for Project A.
It replaces the older `final_acceptance.ps1` checklist.

## 0. Release context

- Current release target: `v1.0.2`.
- Hosted production branch: `production/v1.0.2` on `https://github.com/wyjhfl/project-a-rag-platform`.
- Git history is reconstructed. Keep `docs/release_lineage_notice.md` in every release.
- Do not move old tags. Create a new tag for new production changes.

## 1. Pre-flight checks

These must pass before running the full gate:

- Python 3.11+ or 3.12 available.
- npm available.
- Docker and Docker Compose available.
- Docker Desktop / engine running.
- Frontend dependencies installed: `cd frontend && npm ci`.
- Optional local tool paths may be stored in `scripts/acceptance.defaults.json` copied from `scripts/acceptance.defaults.example.json`.

## 2. One-command production gate

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\final_production_acceptance.ps1 `
  -PythonExe "D:\codex安装\tools\Python312\python.exe" `
  -NpmCmd "D:\codex安装\tools\nodejs\npm.cmd" `
  -RunFullE2E
```

Expected result: all checks pass and the script exits with code `0`.
Any failed step is a release blocker.

## 3. Gate coverage

The script validates:

1. Full backend tests: `python -m pytest backend/tests -q`
2. Ruff check: `python -m ruff check backend`
3. Frontend build: `npm run build`
4. OpenAPI types: `npm run api:types`
5. E2E test discovery: `npm run e2e -- --list`
6. Secret scan: `python scripts/secret_scan.py --dir .`
7. Production Docker Compose config: `docker compose config`
8. Demo Docker Compose config: `docker compose -f docker-compose.demo.yml config`
9. PostgreSQL smoke using real `PostgresStore`
10. Redis rate-limit unit tests
11. Redis rate-limit smoke with Docker Redis
12. PostgreSQL worker stress
13. Full Playwright E2E when `-RunFullE2E` is provided

## 4. Production configuration guardrails

Before deployment, verify `.env` is based on `.env.production.example` and all placeholders are replaced:

- `AUTH_ENABLED=true`
- At least one of `VIEWER_API_KEY`, `OPERATOR_API_KEY`, `ADMIN_API_KEY` set; production should set all three.
- `CORS_ALLOW_ORIGINS` is an explicit frontend origin, not `*`.
- `POSTGRES_PASSWORD` is changed and matches the password in `DATABASE_URL`.
- `RATE_LIMIT_BACKEND=redis` and `RATE_LIMIT_REDIS_URL=redis://redis:6379/0` for multi-instance production.
- `CACHE_ENABLED=true` and `REDIS_URL=redis://redis:6379/0` when Redis cache is required.
- `LLM_API_KEY` and provider settings are injected via environment variables, not committed.

## 5. Manual smoke after deployment

- `GET /healthz` returns `200`.
- `GET /readyz` returns `ok` or `degraded`; investigate all degraded optional dependencies.
- `GET /metrics` contains `project_a_request_total` after traffic.
- Frontend loads from the deployed web origin.
- API key modal can save a key, and protected operations return expected `401/403/200` behavior.
- Create an ingest job, observe `PENDING/RUNNING -> SUCCEEDED` or `CANCELLED`.
- Check audit events for `job.create`, `job.succeeded`/`job.failed`/`job.cancelled`.

## 6. Release decision

A production release may be tagged and pushed only after:

- automated gate passes,
- working tree is clean,
- release notes are updated,
- lineage notice remains present,
- GitHub branch and tag push are verified with `git ls-remote`.
