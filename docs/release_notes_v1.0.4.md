# Release Notes - v1.0.4

## Summary

`v1.0.4` is the immutable production landing tag for the latest accepted production branch state. It preserves the `v1.0.3` production baseline and includes the post-tag worker hardening fixes that were validated on `production/v1.0.3`.

This release remains based on reconstructed Git history. See:

- `docs/release_lineage_notice.md`
- `docs/canonical_repo_decision.md`

## Key changes since v1.0.3

### Worker cancellation and timeout hardening

- Job cancellation requests are atomized at the storage/service boundary.
- Stale job timeout recovery is atomized so competing workers do not double-recover the same job.
- Long-running jobs heartbeat during executor execution so valid long tasks are not marked stale.
- Heartbeat checks now convert `cancel_requested` RUNNING jobs to `CANCELLED`, preventing cancelled long-running jobs from being kept alive indefinitely.

### Guardrail tests

- Added/kept regression coverage for atomic cancellation, stale timeout recovery, long-running heartbeat, and heartbeat-driven cancellation.

### Version metadata

- Python package version updated to `1.0.4`.
- Frontend package and lockfile versions updated to `1.0.4`.
- README release pointers updated to `v1.0.4` and `production/v1.0.4`.

## Final validation evidence

The final production acceptance gate passed with Full E2E enabled on 2026-06-08:

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

Additional fresh checks before the v1.0.4 metadata commit:

```text
backend/tests: 182 passed, 1 warning
ruff check backend scripts: All checks passed
frontend build: passed
api:types: passed
E2E list: 21 tests in 8 files
```

## Hosted handoff

The project owner approved using:

```text
https://github.com/wyjhfl/project-a-rag-platform
```

Production code is pushed to the versioned branch:

```text
production/v1.0.4
```

Do not force-push over the older public-delivery `main` branch.

## Remaining known risks

- Git lineage is reconstructed and not the original pre-recovery history.
- Production deployments should run the final production acceptance script in their own environment before rollout.
- Further post-v1.0.4 work can focus on OTel/Grafana dashboards, Alembic migrations, and broader multi-worker load testing.
