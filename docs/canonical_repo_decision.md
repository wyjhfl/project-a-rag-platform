# Canonical Repository Decision ? v1.0.1

## Decision status

**Decision**: Treat the current local repository as the new canonical engineering baseline for Project A production releases, starting from the reconstructed `v1.0.0` lineage and the `v1.0.1` release.

This decision is pragmatic, not historical: the current codebase has passed the production acceptance gate, but the original Git lineage is not available locally.

## Current facts

- The original `e64b095` release-gate commit is **not present** in the current local Git history.
- The current `v1.0.0` tag points to reconstructed commit `111066c`.
- The current `v1.0.1-rc.1` tag points to `19c3467`.
- The remote `origin` points to `https://github.com/wyjhfl/project-a-rag-platform.git`, which is a different public delivery / portfolio repository.
- The current `origin` must **not** be used as the production canonical remote for this reconstructed engineering history.

## Recommended canonical strategy

Use the current local repository as the new canonical source of truth **only after explicitly accepting the reconstructed-history risk**.

Recommended next step:

1. Create a new private or production Git repository dedicated to this production-ready Project A lineage.
2. Push the current `main` branch and tags to that new remote.
3. Keep `docs/release_lineage_notice.md` and this decision document in the repository permanently.
4. Do not force-push or overwrite the current public `origin` repository.

## Allowed options

### Option A ? New canonical remote (recommended)

Create a new remote repository and push current `main` plus tags:

```powershell
git remote add production-origin <NEW_CANONICAL_REMOTE_URL>
git push production-origin main
git push production-origin --tags
```

Use this only with a newly created repository intended for this reconstructed production lineage.

### Option B ? Local canonical with release bundle backup

Keep the local repository as canonical for now and distribute/backup via `git bundle`:

```powershell
git bundle create dist_release/project-a-v1.0.1.bundle --all
```

This is acceptable for local handoff, but weaker than a managed remote repository.

### Option C ? Restore original history if found later

If a trusted backup containing the original `e64b095` lineage is later found:

1. Restore that repository separately.
2. Re-apply post-v1.0 changes as patches or cherry-picks.
3. Re-run the full production acceptance gate.
4. Re-issue release tags from the restored lineage.

## Prohibited actions

- Do **not** push `main` or release tags to the current `origin`.
- Do **not** force-push over the public delivery repository.
- Do **not** delete `docs/release_lineage_notice.md`.
- Do **not** claim that the current `v1.0.0` tag is the original `e64b095` tag.
- Do **not** create further release tags without passing `scripts/final_production_acceptance.ps1 -RunFullE2E`.

## Release readiness impact

The reconstructed lineage is a release-management risk, not a current-runtime correctness failure. Current production readiness depends on:

- backend test suite passing,
- ruff passing,
- frontend build passing,
- Docker compose production/demo config passing,
- PostgreSQL smoke passing,
- Redis rate-limit smoke passing,
- PostgreSQL worker stress passing,
- Full Playwright E2E passing,
- final production acceptance passing.

As of the `v1.0.1` readiness process, these checks must be re-run before the final tag is considered valid.

## Local canonical remote created

A local bare canonical remote has been created for safe handoff without touching the existing public `origin`:

```text
D:\wyj-hfl-shizhanxiangmu\project-a-rag-platform-canonical.git
```

It contains the production release tags and the current handoff branch:

```text
v1.0.1 tag -> 3c2ce62
main -> current handoff branch tip
tags: v1.0.0, v1.0.1-rc.1, v1.0.1
```

The `v1.0.1` release tag remains fixed at `3c2ce62`. Later documentation-only handoff commits may exist on `main` without moving the release tag.

Verification clone path used during release readiness:

```text
D:\wyj-hfl-shizhanxiangmu\project-a-rag-platform-canonical-verify
```

The bare repository `HEAD` has been set to `refs/heads/main`, and clone verification succeeds.

This local remote is a safe staging canonical. If a hosted canonical repository is later created, push from this local `production-origin` or from the working tree to the new hosted remote. Do not push to the current public `origin`.
