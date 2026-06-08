# Release Notes - v1.0.5

## Summary

`v1.0.5` is the resume/interview showcase release for Project A. It builds on the `v1.0.4` production baseline and focuses on making the project easier to understand, demo, and defend in technical interviews.

The core production capabilities remain intact: FastAPI backend, Vue 3 console, RAG quality evidence, async Jobs, audit logs, Prometheus metrics, OpenAPI type generation, Docker Compose validation, PostgreSQL/Redis smoke checks, worker stress, and Full E2E.

This release still uses reconstructed Git history. The detailed historical recovery notes were intentionally removed from the public showcase tree to keep the repository focused; the current `v1.0.5` code, tests, docs, tag, and CI state are the authoritative showcase baseline.

## Key changes since v1.0.4

### Interview showcase polish

- Reworked README top section for resume delivery: 30-second pitch, bilingual resume bullets, demo route, production gate, and interview-facing evidence links.
- Added `docs/resume_interview_showcase.md`.
- Added `docs/interview_demo_script.md`.
- Added `docs/interview_questions.md`.
- Added `docs/demo_guide.md`.

### Architecture and quality UI

- Added an `Architecture` console page with:
  - system layer map,
  - RAG data flow,
  - Job / Worker flow,
  - observability flow,
  - final production acceptance gate,
  - copyable Mermaid architecture graph.
- Added a `Quality` console page with:
  - regression pass evidence,
  - `context_precision`,
  - `faithfulness`,
  - `context_recall`,
  - Bad Case boundaries,
  - low-score Trace review,
  - production tradeoff lane.

### Jobs / Worker interview depth

- Added Worker / queue architecture section to Jobs page.
- Documented `claim_next_job`, `heartbeat`, `cancel_requested`, safe error summaries, PostgreSQL worker stress, and the path toward external queues such as Celery/RQ/Redis Queue.

### Observability and error traceability polish

- System Status page surfaces `/metrics` summary in the UI.
- API error alerts display and copy Request ID.
- README and interview docs connect Request ID, audit events, metrics, and final production acceptance into a single troubleshooting story.

## Final validation evidence

The final production acceptance gate passed with Full E2E enabled:

```text
13/13 ALL CHECKS PASSED
  1. Full Backend Tests: PASSED
  2. Ruff Check: PASSED
  3. Frontend Build: PASSED
  4. OpenAPI Drift Check: PASSED
  5. E2E List: PASSED
  6. Secret Scan: PASSED
  7. Docker Compose Production Config: PASSED
  8. Docker Compose Demo Config: PASSED
  9. PostgreSQL Smoke: PASSED
  10. Redis Rate Limit Unit Tests: PASSED
  11. Redis Rate Limit Smoke: PASSED
  12. PostgreSQL Worker Stress: PASSED
  13. Full E2E: PASSED
```

Fresh local checks before the `v1.0.5` release commit:

```text
backend/tests: 204 passed, 1 warning
ruff check backend scripts: All checks passed
frontend build: passed
OpenAPI drift check: passed
E2E list: 33 tests in 11 files
secret scan: No secrets found
docker compose config: passed
docker compose demo config: passed
```

## Recommended resume demo route

1. Acceptance: project pitch and evidence entry point.
2. Architecture: system layers, RAG flow, Worker flow, observability, production gate.
3. Quality: RAG metrics, Bad Case boundaries, Trace review, tradeoffs.
4. System Status: release, healthz/readyz, metrics, Request ID.
5. Jobs: async worker lifecycle, claim/cancel/retry/timeout/heartbeat, queue evolution.
6. Chat / Tickets / Evaluations / Audit: grounded answer, escalation, evaluation, traceability.

## Remaining known risks

- Git lineage is reconstructed and should remain transparent in interviews and release notes.
- Grafana/OTel is not yet integrated; `/metrics` is available and parsed in the UI.
- Alembic migrations are not yet introduced.
- The built-in JobService is appropriate for demo and MVP semantics; external queues remain the recommended multi-instance evolution path.
