# PR: Upgrade Project A to Agentic RAG Diagnosis Platform

## Summary

- Upgrade Project A from an enterprise RAG Ops console into an enterprise Agentic RAG diagnosis platform without turning it into a multi-agent project.
- Add a single diagnosis controller for safety check, query routing, adaptive retrieval, risk detection, ticket escalation, trace persistence, and GraphRAG relation display.
- Productize observability and delivery foundations with Prometheus/Grafana demo stack, Alembic migration skeletons, OpenAPI type generation, evaluation metrics, and updated interview-facing documentation.

## Key Changes

- Added `POST /api/v1/agent/diagnose` for Agentic RAG diagnosis decisions: `answer`, `refuse`, and `escalate`.
- Added trace APIs: `GET /api/v1/rag/traces` and `GET /api/v1/rag/traces/{trace_id}`.
- Added GraphRAG relation API: `GET /api/v1/rag/graph/relations`.
- Added frontend `Agentic RAG` route at `#/agentic` with diagnosis result, tool-call timeline, adaptive retrieval details, trace id, and graph relation display.
- Added RAG trace persistence, Agentic RAG evaluation cases, metrics counters, Prometheus/Grafana config, and Alembic migration skeletons.
- Pruned stale development-only acceptance/provider scripts and aligned README validation counts with the current test suite.

## Positioning

This PR keeps Project A focused on **Enterprise Agentic RAG Diagnosis**:

- It is not a general multi-agent collaboration platform.
- It uses one RAG-focused diagnosis controller to make retrieval, refusal, escalation, and trace decisions explainable.
- It complements `project-b-multi-agent` instead of overlapping with it.

## Test Plan

- `python -m pytest backend/tests -q` -> `185 passed, 1 warning`
- `python -m ruff check backend scripts` -> passed
- `python scripts/secret_scan.py` -> `No secrets found`
- `npm --prefix frontend run build` -> passed
- `npm --prefix frontend run api:check` -> passed with `PROJECT_A_PYTHON_EXE` pointing to the project Python runtime
- `npm --prefix frontend run e2e -- --list` -> `35 tests in 12 files`
- `docker compose config` -> passed
- `docker compose -f docker-compose.demo.yml config` -> passed

## Known Notes

- `npm ci` currently reports 4 audit findings. They are intentionally not fixed in this PR to avoid mixing dependency remediation with the Agentic RAG feature upgrade.
- OpenTelemetry is still a future enhancement. This PR adds Prometheus/Grafana demo observability rather than full distributed tracing.
- Alembic is introduced as a migration skeleton while the existing SQLite/PostgreSQL auto-create path remains for demo safety.
