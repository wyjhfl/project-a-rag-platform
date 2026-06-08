# Release Notes — v1.0.1-rc.1

## 版本范围

- **From**: v1.0.0 (reconstructed tag, commit `111066c`)
- **To**: v1.0.1-rc.1 (commit to be tagged)

## 本次主要变化

### Redis-backed Rate Limiting

- `RateLimiter` ABC → `MemoryRateLimiter` (sliding window) + `RedisRateLimiter` (fixed window with Lua script)
- Redis Lua script: atomic INCR + EXPIRE for RPM (minute bucket, TTL 61s) and burst (second bucket, TTL 2s)
- Redis key format: `project_a:ratelimit:rpm:{key}:{minute_bucket}` / `project_a:ratelimit:burst:{key}:{second_bucket}`
- When Redis is unavailable: readyz returns degraded/error, requests are denied (429), NOT silently degraded to memory
- Config: `RATE_LIMIT_BACKEND=memory|redis`, `RATE_LIMIT_REDIS_URL=redis://...`

### PostgreSQL Worker Stress Validation

- `FOR UPDATE SKIP LOCKED` for PostgreSQL claim_next_job
- `BEGIN IMMEDIATE` for SQLite claim_next_job (atomic)
- Worker stress test: 50 jobs / 6 workers, 0 duplicate claims

### Job Worker Recovery Consistency

- `JobService` API unified: `claim_job`, `complete_job` (returns bool), `fail_job` (returns bool), `cancel_running_job` (returns bool), `timeout_stale_jobs` (retry_count increment)
- Job states: PENDING → RUNNING → SUCCEEDED/FAILED/CANCELLED/RETRYING
- `cancel_running_job` bypasses retry → CANCELLED, sets `cancel_requested=True`
- `timeout_stale_jobs` increments retry_count; RETRYING if retries remain, FAILED if exhausted
- `job_worker.run_job()` supports `document.ingest` and `evaluation.run` types

### Metrics Naming Recovery

- Prometheus-style output: `project_a_request_total`, `project_a_error_total`, `project_a_job_total`, `project_a_uptime_seconds`
- HELP/TYPE headers included

### PowerShell 5 Compatibility

- Replaced all `??` null coalescing operators with PS5-compatible `if ($env:VAR) { $env:VAR } else { "default" }`
- Fixed `$ErrorActionPreference` handling for npm stderr output

### Redis Smoke Clean Output

- Redis unavailable scenario: no traceback, no absolute paths, no `.pg_deps` internal stack
- Output only safe summary lines ending with `PASSED`
- Logging level set to CRITICAL during Redis unavailable tests

### Restored Backend Test Coverage

- Test files restored from 3 to 16 (147 total tests)
- Restored: API, auth, health/readiness, RAG security, ticket workflow, release scenarios, acceptance overview, enterprise API, hybrid retrieval, public release sanitization, AV13/AV23/AV24 acceptance
- Storage API: added `add_document`, `add_chat_record`, `add_token_usage`, `upsert_ticket`, `get_ticket`, `get_ticket_by_idempotency_key`, `list_tickets`
- Readyz: optional dep failure → 200 degraded (not 503)
- Acceptance overview: provider panel returns "passed" when LLM provider configured

### Full Production Acceptance 13/13

- Auto-start backend + frontend preview in Full E2E step
- Process cleanup on exit
- Docker mandatory check (no false pass)

## 已验证项目

| 检查项 | 结果 |
|---|---|
| Backend tests | 147 passed, 1 warning |
| Ruff check | All checks passed |
| Frontend build | Passed |
| api:types | Passed |
| Docker compose production config | Passed |
| Docker compose demo config | Passed |
| PostgreSQL smoke | 10/10 PASSED |
| Redis rate limit unit tests | Passed |
| Redis rate limit smoke | 7/7 PASSED |
| PostgreSQL worker stress | PASSED (0 duplicates) |
| Full E2E | PASSED (21 tests) |
| Secret scan | No secrets found |
| Final production acceptance | 13/13 PASSED |

## 已知风险

1. **Git lineage reconstructed**: The original `e64b095` commit history is not present locally. The current `v1.0.0` tag at `111066c` is a reconstructed tag created after `.git` directory corruption.
2. **Remote origin mismatch**: The remote `origin` points to `https://github.com/wyjhfl/project-a-rag-platform.git`, which is a different public delivery repository (A-v3.5 portfolio version). It cannot be used to recover the original engineering history.
3. **RC validity**: This RC is valid only if the project owner accepts the reconstructed history. See [docs/release_lineage_notice.md](release_lineage_notice.md) for details.

## 回滚策略

### 代码回滚

```bash
git checkout v1.0.0  # reconstructed tag
```

### 历史恢复

If the original history must be recovered:
1. Restore from a trusted external backup that contains the original `.git` directory
2. Re-apply the changes from commits `43d700d`, `8f07973`, `c2afe65` as patches

### 数据层面注意

- **Jobs**: SQLite/PostgreSQL `jobs` table schema is stable; rollback does not require migration
- **Rate limit**: Redis keys are ephemeral (TTL-based); rollback simply stops using them
- **PostgreSQL schema**: `FOR UPDATE SKIP LOCKED` is standard SQL; no schema change on rollback
