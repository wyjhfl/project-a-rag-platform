# Canonical Repository Decision — v1.0.2

## Decision status

**Decision**: Treat the current repository contents as the accepted reconstructed production baseline for Project A, with `v1.0.2` as the current enterprise landing release.

This is a pragmatic engineering decision, not a claim that the original pre-recovery Git history was preserved.

## Current facts

- The original `e64b095` release-gate commit is **not present** in the current local Git history.
- The current `v1.0.0` tag points to reconstructed commit `111066c`.
- The current `v1.0.1` tag points to `3c2ce62`.
- The current `v1.0.2` tag points to `4090e4d`.
- The project owner approved using `https://github.com/wyjhfl/project-a-rag-platform` as the hosted remote for this production handoff.
- The older public-delivery `main` branch must not be force-overwritten. Production releases are published on versioned production branches.

## Hosted production remote

Production handoff branch:

```text
origin/production/v1.0.2 -> 4090e4d
```

Release tag:

```text
v1.0.2 -> 4090e4d
```

Remote URL:

```text
https://github.com/wyjhfl/project-a-rag-platform
```

## Release readiness rule

Do **not** create or move a production release tag unless the full production gate passes:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\final_production_acceptance.ps1 `
  -RunFullE2E
```

For `v1.0.2`, the final gate passed 13/13 checks before the tag and branch were pushed.

## Lineage warning

Keep `docs/release_lineage_notice.md` permanently. All release notes must state that the release is based on reconstructed history.

## Local canonical backup

A local bare backup may still exist at:

```text
D:\wyj-hfl-shizhanxiangmu\project-a-rag-platform-canonical.git
```

The hosted GitHub production branch/tag are now the practical handoff target for `v1.0.2`.
