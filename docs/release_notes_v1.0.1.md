# Release Notes ? v1.0.1

## Release scope

- **Base**: `v1.0.0` reconstructed tag at commit `111066c`
- **RC**: `v1.0.1-rc.1` at commit `19c3467`
- **Final**: `v1.0.1` at the release-readiness commit

This release is based on reconstructed Git history. See:

- `docs/release_lineage_notice.md`
- `docs/canonical_repo_decision.md`

## Summary

`v1.0.1` finalizes the production landing work after the reconstructed-history recovery. It keeps the runtime behavior from `v1.0.1-rc.1`, adds final canonical repository decision documentation, and defines local release artifacts for handoff and backup.

## Main changes since reconstructed v1.0.0

### Production runtime hardening

- Redis-backed rate limiting with atomic Redis Lua counters.
- DB-backed job lease worker validation for PostgreSQL and SQLite paths.
- PostgreSQL worker stress coverage with duplicate-claim detection.
- Redis unavailable behavior: readiness degraded/error and requests denied instead of silently falling back to memory.

### Recovery and consistency fixes

- Restored backend test coverage from 3 files to 16 files.
- Recovered `app.job_worker` and `app.migrations` modules.
- Reconciled `JobService` worker API semantics.
- Restored storage compatibility methods used by the API and release tests.
- Restored Prometheus-style metric names: `project_a_request_total`, `project_a_error_total`, `project_a_job_total`, `project_a_uptime_seconds`.
- Fixed PowerShell 5 compatibility in E2E scripts.
- Cleaned Redis smoke output: no traceback, no local absolute paths.

### Release governance

- Added `docs/release_lineage_notice.md`.
- Added `docs/canonical_repo_decision.md`.
- Added `docs/release_artifacts_v1.0.1.md`.
- Kept generated release bundles outside Git via `dist_release/`.
- Explicitly documented that the current `origin` must not be used for production release push.

## Validation evidence

The final release must be considered valid only if these commands pass at release time:

```text
pytest backend/tests -q
ruff check backend
frontend build
frontend api:types
scripts/final_production_acceptance.ps1 -RunFullE2E
```

The `v1.0.1` final release readiness run records:

```text
Backend tests: 147 passed, 1 warning
Ruff: All checks passed
Frontend build: passed
api:types: passed
Final production acceptance: 13/13 passed
```

The final production acceptance includes:

1. Full Backend Tests
2. Ruff Check
3. Frontend Build
4. OpenAPI Types
5. E2E List
6. Secret Scan
7. Docker Compose Production Config
8. Docker Compose Demo Config
9. PostgreSQL Smoke
10. Redis Rate Limit Unit Tests
11. Redis Rate Limit Smoke
12. PostgreSQL Worker Stress
13. Full E2E

## Known risks

1. **Reconstructed Git lineage**: the original `e64b095` history is not present locally.
2. **Remote mismatch**: current `origin` points to a different public delivery repository and must not be used for this production lineage.
3. **Operational handoff**: a new canonical production remote should be created before team-based collaboration.
4. **Package version semantics**: Python/frontend package versions may still be `1.0.0`; release identity is represented by Git tag `v1.0.1`.

## Rollback

Code rollback:

```powershell
git checkout v1.0.0
```

Artifact restore:

```powershell
git clone dist_release\project-a-v1.0.1.bundle project-a-restored
cd project-a-restored
git tag --list
git log --oneline --decorate -5
```

Data notes:

- Redis rate-limit keys are TTL-based and can be discarded safely.
- Job tables remain schema-compatible for current production landing scope.
- PostgreSQL worker claim behavior uses locking semantics, not a destructive schema migration.

## Next step

Create a new canonical private/production remote and push this lineage there. Do not push this lineage to the current `origin`.
