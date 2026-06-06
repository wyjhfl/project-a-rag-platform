# Release Notes - v1.0.3

## Summary

`v1.0.3` is the final production landing release after the v1.0.2 hosted handoff. It preserves the v1.0.2 enterprise landing baseline and adds the final worker-state hardening needed for safer multi-worker execution.

This release is based on reconstructed Git history. See:

- `docs/release_lineage_notice.md`
- `docs/canonical_repo_decision.md`

## Key changes since v1.0.2

### Job worker correctness

- Added store-level atomic job transitions for SQLite and PostgreSQL:
  - `try_complete_job`
  - `try_fail_job`
  - `try_heartbeat_job`
  - `try_cancel_running_job`
- `JobService` now prefers conditional store updates so worker completion/failure/heartbeat/cancel operations require the job to still be `RUNNING` and owned by the same worker.
- Completion/failure updates do not override `cancel_requested` jobs.
- Retry/failure logic is preserved while moving the critical state transition into the storage layer.

### Guardrail tests

- Added SQLite atomic transition tests for owner checks, cancellation, retry, failure, and JobService integration.
- Added a PostgreSQL guardrail test ensuring the production store declares atomic transition methods and conditional `RUNNING`/`locked_by` checks.

### Version metadata

- Python package version updated to `1.0.3`.
- Frontend package and lockfile versions updated to `1.0.3`.
- README release pointers updated to `v1.0.3` and `production/v1.0.3`.

## Final validation evidence

The final production acceptance gate passed with Full E2E enabled:

```text
13/13 ALL CHECKS PASSED
  1. Full Backend Tests: PASSED
  2. Ruff Check: PASSED
  3. Frontend Build: PASSED
  4. OpenAPI Types: PASSED
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

## Hosted handoff

The project owner approved using:

```text
https://github.com/wyjhfl/project-a-rag-platform
```

Production code is pushed to the versioned branch:

```text
production/v1.0.3
```

Do not force-push over the older public-delivery `main` branch.

## Remaining known risks

- Git lineage is reconstructed and not the original pre-recovery history.
- Production deployments should run the final production acceptance script in their own environment before rollout.
- Further post-v1.0.3 work can focus on OTel/Grafana dashboards, Alembic migrations, and broader multi-worker load testing.
