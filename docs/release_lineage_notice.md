# Release Lineage Notice

## Overview

The current repository history was reconstructed after a local `.git` directory loss. It is **not** the original continuous pre-recovery Git history. Every release from this repository must state this risk clearly.

## Key facts

- The original v1.0.0 release-gate commit `e64b095` is not present in the current local history.
- The current `v1.0.0` tag is a reconstructed tag pointing to `111066c`, not the original `e64b095`.
- The current `v1.0.1` tag points to `3c2ce62`.
- The current `v1.0.2` tag points to `d0c4f94`.
- The project owner approved using `https://github.com/wyjhfl/project-a-rag-platform` as the hosted remote.
- To avoid overwriting the older public-delivery `main` branch, production releases are published on versioned production branches such as `production/v1.0.2`.

## Current production line

```text
production/v1.0.2  versioned production handoff branch; may include post-tag handoff documentation commits
d0c4f94  (tag: v1.0.2) documentation-consistent v1.0.2 release baseline
4090e4d  enterprise landing release checklist
4309e9f  PostgreSQL Store + Redis/compose/worker hardening
6aa1a44  v1.0.1 handoff docs
3c2ce62  (tag: v1.0.1)
111066c  (tag: v1.0.0 reconstructed)
```

## Governance conclusion

This is a reconstructed production lineage. It can be used as the new production handoff baseline, but it must not be represented as preserving the original Git history before `e64b095`.

## Release rules

- Do not force-push over remote `main`.
- Use `production/vX.Y.Z` branches for production releases.
- Create and push release tags only after `scripts/final_production_acceptance.ps1 -RunFullE2E` passes.
- Keep the reconstructed-history notice in release notes.

---

Last updated: 2026-06-06
