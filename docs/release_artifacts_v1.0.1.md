# Release Artifacts ? v1.0.1

This document describes the local release artifacts for Project A `v1.0.1`.

## Important note about checksums

The source zip cannot contain a document that records its own final SHA256 without creating a self-referential checksum problem. Therefore:

- this document records the artifact policy and recovery commands;
- the authoritative generated checksums are written to `dist_release/SHA256SUMS.txt` after the `v1.0.1` tag is created;
- `dist_release/` is intentionally ignored by Git and should be stored externally as a release deliverable.

## Expected artifact files

Generated files:

```text
dist_release/project-a-v1.0.1.bundle
dist_release/project-a-v1.0.1-source.zip
dist_release/SHA256SUMS.txt
```

## Generation commands

Run from the repository root after the final `v1.0.1` tag exists:

```powershell
New-Item -ItemType Directory -Force -Path dist_release | Out-Null
git bundle create dist_release/project-a-v1.0.1.bundle --all
git archive --format=zip --output=dist_release/project-a-v1.0.1-source.zip v1.0.1
Get-FileHash dist_release\project-a-v1.0.1.bundle -Algorithm SHA256
Get-FileHash dist_release\project-a-v1.0.1-source.zip -Algorithm SHA256
```

## Restore from bundle

```powershell
git clone dist_release\project-a-v1.0.1.bundle project-a-restored
cd project-a-restored
git tag --list
git log --oneline --decorate -5
```

Expected tags in the restored repository:

```text
v1.0.0
v1.0.1-rc.1
v1.0.1
```

## Release lineage warning

The `v1.0.1` artifacts are based on reconstructed history. See:

- `docs/release_lineage_notice.md`
- `docs/canonical_repo_decision.md`

Do not push these artifacts or tags to the existing public `origin`; create a new canonical remote if a remote handoff is required.

## Local canonical remote

In addition to the bundle and source zip, the release tags and current handoff branch have been pushed to a local bare canonical remote:

```text
D:\wyj-hfl-shizhanxiangmu\project-a-rag-platform-canonical.git
```

Verification command:

```powershell
git clone D:\wyj-hfl-shizhanxiangmu\project-a-rag-platform-canonical.git project-a-canonical-verify
cd project-a-canonical-verify
git log --oneline --decorate -5
git tag --list
```


The `v1.0.1` source zip is generated from the immutable `v1.0.1` tag. The bundle may also include later documentation-only handoff commits reachable from `main`.
