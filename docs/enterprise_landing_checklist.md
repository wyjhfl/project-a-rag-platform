# Enterprise Landing Checklist — v1.0.2

## Current go/no-go

Project A is suitable for a controlled enterprise pilot and small production landing. The v1.0.2 hardening gate has passed.

It is not yet a regulated/high-scale enterprise platform without additional SSO, backup, observability dashboarding, and formal migration governance.

## What v1.0.2 fixes

- Production compose defaults are fail-closed: authentication and rate limiting default to enabled.
- Redis-backed rate limiting is configured in production compose and `.env.production.example`.
- Production Docker image installs PostgreSQL, Redis, and Milvus client extras.
- `STORAGE_BACKEND=postgres` now uses the real `PostgresStore` instead of silently falling back to SQLite.
- PostgreSQL smoke uses the real `PostgresStore` and `JobService` paths.
- Production worker module has an executable loop for claimed jobs.
- Python and frontend package versions are aligned to `1.0.2`.

## Required production environment

| Area | Required setting |
|---|---|
| Auth | `AUTH_ENABLED=true`; viewer/operator/admin keys injected securely |
| Storage | PostgreSQL via `STORAGE_BACKEND=postgres` and `DATABASE_URL` |
| Vector DB | Milvus via `VECTOR_BACKEND=milvus` or explicitly switch to Chroma for single-node pilots |
| Cache | Redis via `CACHE_ENABLED=true` and `REDIS_URL` |
| Rate limit | Redis backend via `RATE_LIMIT_BACKEND=redis` |
| CORS | Explicit frontend origin |
| Metrics | `/metrics` enabled and scraped by an external system |
| Worker | `worker` service enabled for background jobs |

## Remaining risks

| Risk | Level | Mitigation |
|---|---|---|
| Reconstructed Git lineage | High governance risk | Keep lineage notice; use new production branch/tag as the accepted baseline |
| No SSO/OIDC | Medium | API key RBAC is acceptable for pilot; add SSO before broad enterprise rollout |
| No Grafana/OTel dashboards | Medium | `/metrics` exists; add Prometheus/Grafana/OTel post-landing |
| No Alembic framework | Low/Medium | Current schema is initialized in stores; add Alembic before frequent DB evolution |
| Compose startup races | Low | Services use Docker restart policy; verify `/readyz` after startup |
| Vendor chunk size | Low | Accept for pilot; optimize frontend bundling later |

## GitHub handoff policy

The project owner approved using `https://github.com/wyjhfl/project-a-rag-platform` as the hosted remote.

To avoid overwriting the older public-delivery `main`, production code is pushed to versioned production branches such as:

```text
production/v1.0.2
```

Release tags such as `v1.0.2` may be pushed to the same remote after the final production acceptance gate passes.
