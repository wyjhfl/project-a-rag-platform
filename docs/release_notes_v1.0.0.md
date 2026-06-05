# Release Notes: v1.0.0

**Release Date**: 2026-06-05
**Baseline**: v1.0.0-rc.1
**Branch**: production-landing

## Production Landing Commits

| Commit | Description |
|--------|-------------|
| e0d5bac | feat: production landing hardening |
| 42ab0cd | fix: harden production landing worker and acceptance gates |
| 5b23d19 | fix: validate production landing runtime gates |

## Backend Capabilities

- **FastAPI** REST API with healthz/readyz/health endpoints
- **SQLite** (demo) and **PostgreSQL** (production) storage backends
- **Chroma** (demo) and **Milvus** (production) vector backends
- **Job system**: document.ingest, evaluation.run with atomic claim
- **Auth**: API Key based (viewer/operator/admin roles)
- **Rate limiting**: RPM + burst dual enforcement, health endpoints exempt
- **Metrics**: request count, latency, errors, job status via /metrics
- **Audit events**: job.claimed/retrying/timeout/cancelled/succeeded/failed
- **Secret scan**: CI-grade pattern detection

## Frontend Capabilities

- **Vue 3 + Vite + TypeScript + Element Plus + Pinia**
- 8 pages: Acceptance, System Status, Documents, Jobs, Audit, Chat, Tickets, Evaluations
- API Key configuration dialog with role selection
- Async job management with search
- OpenAPI-generated TypeScript types

## Worker / Job Production Semantics

- **Atomic claim**: SQLite conditional UPDATE, PostgreSQL FOR UPDATE SKIP LOCKED
- **RUNNING cancel**: `cancel_running_job()` bypasses retry, directly sets CANCELLED
- **PENDING/RETRYING cancel**: Directly CANCELLED, no cancel_requested flag
- **Timeout**: `timeout_stale_jobs()` marks stale RUNNING jobs as FAILED with retry
- **Audit trail**: Every job state transition recorded
- **Metrics**: `project_a_job_total{status=...}` recorded on completion/cancellation

## PostgreSQL Smoke Result

- Docker-based ephemeral PostgreSQL 16-alpine
- 10/10 tests passed: create, get, claim, double-claim guard, complete, cancel, list
- Container auto-cleanup on exit

## Full E2E Result

- 21/21 Playwright tests passed against live demo services
- Chromium, 8 workers, ~6s total
- Covers: acceptance, system-status, api-key, documents, evaluations, jobs, audit, tickets

## final_production_acceptance Result

- 10/10 ALL CHECKS PASSED (with -RunFullE2E)
- Steps: full backend tests, ruff, frontend build, api:types, e2e --list, secret scan, docker compose config (prod+demo), postgres smoke, full e2e

## Known Risks

| Risk | Level | Mitigation |
|------|-------|------------|
| Docker not in default PATH | Low | Add Docker bin to PATH manually |
| psycopg_pool not in default pip | Low | Production Docker image includes it |
| E2E depends on live demo services | Low | e2e_demo_smoke.ps1 checks before run |
| No Redis-backed rate limiting | Low | In-memory works for single-instance |
| No Alembic migrations | Low | Schema version tracked in DB |
| No Grafana/OTel integration | Low | /metrics endpoint available for scraping |

## Rollback

```bash
git checkout v1.0.0-rc.1
# or
git revert <commit-hash>
```

Demo stack uses SQLite; no data migration needed for rollback.

## Upgrade from v1.0.0-rc.1

1. `git pull origin production-landing`
2. `pip install -r backend/requirements.txt`
3. `cd frontend && npm install && npm run build`
4. Backend: no schema change needed (SQLite demo)
5. Production PostgreSQL: schema auto-migrates on startup
6. Restart backend and worker services
