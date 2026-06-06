# Release Notes — v1.0.2

## Summary

`v1.0.2` is the final enterprise landing hardening release after the reconstructed-history recovery and v1.0.1 handoff.

This release is based on reconstructed Git history. See:

- `docs/release_lineage_notice.md`
- `docs/canonical_repo_decision.md`

## Key changes since v1.0.1

### Production runtime correctness

- Added a real `PostgresStore` implementation for `STORAGE_BACKEND=postgres`.
- Updated the storage factory so production no longer silently falls back to SQLite.
- Updated PostgreSQL smoke to validate the real `PostgresStore` + `JobService` path.
- Added an executable production worker loop in `app.job_worker`.
- Worker processing now records terminal job metrics and handles cancellation before and after execution.

### Production defaults and packaging

- Production compose defaults `AUTH_ENABLED=true` and `CACHE_ENABLED=true`.
- Production compose defaults rate limiting to Redis: `RATE_LIMIT_BACKEND=redis`.
- `.env.production.example` documents `RATE_LIMIT_BACKEND` and `RATE_LIMIT_REDIS_URL`.
- Docker image installs production extras: Redis, PostgreSQL, and Milvus clients.
- Python and frontend package versions are aligned to `1.0.2`.

### Guardrail tests and docs

- Added enterprise landing guardrail tests for compose/env/Dockerfile/storage factory/worker behavior.
- Rewrote final acceptance checklist for `scripts/final_production_acceptance.ps1`.
- Added enterprise landing checklist with go/no-go and remaining risks.

## Validation required for final tag

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\final_production_acceptance.ps1 `
  -PythonExe "D:\codex安装\tools\Python312\python.exe" `
  -NpmCmd "D:\codex安装\tools\nodejs\npm.cmd" `
  -RunFullE2E
```

The release is valid only if all gate steps pass.

## Hosted handoff

The project owner approved using:

```text
https://github.com/wyjhfl/project-a-rag-platform
```

Production code should be pushed to the versioned branch:

```text
production/v1.0.2
```

Do not force-push over the older public-delivery `main` branch.


## Final validation evidence

Before the hosted branch/tag handoff, the final production acceptance gate passed:

```text
13/13 ALL CHECKS PASSED
```

The remote handoff target is:

```text
origin/production/v1.0.2 -> 4090e4d initially; updated by documentation consistency commit before final handoff.
v1.0.2 tag -> final documentation-consistent commit.
```
