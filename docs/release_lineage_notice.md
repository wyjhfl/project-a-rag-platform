# Release Lineage Notice

## 概述

当前仓库的 Git 历史经历过 `.git` 目录损毁和重建，**不是原始的连续提交历史**。任何基于此仓库的 release 都必须明确此风险。

## 关键事实

- 原始 v1.0.0 release-gate commit `e64b095` 不在当前本地历史中。
- 当前 `v1.0.0` tag 是 reconstructed tag，指向 `111066c`，不是原始 `e64b095`。
- 当前 `v1.0.1` tag 指向 `3c2ce62`。
- 当前 `v1.0.2` tag 指向 `4090e4d`。
- 项目 owner 已确认使用 `https://github.com/wyjhfl/project-a-rag-platform` 作为托管远程。
- 为避免覆盖历史 public-delivery `main`，生产版本发布在 `production/v1.0.2` 等 versioned production branches。

## 当前生产线

```text
4090e4d  (tag: v1.0.2, origin/production/v1.0.2) enterprise landing hardening
4309e9f  PostgreSQL Store + Redis/compose/worker hardening
6aa1a44  v1.0.1 handoff docs
3c2ce62  (tag: v1.0.1)
111066c  (tag: v1.0.0 reconstructed)
```

## 治理结论

这是一条 reconstructed production lineage。它可以作为新的生产交付基线使用，但不能声称保留了原始 `e64b095` 之前的可信 Git 历史。

## 发布规则

- 不要强推覆盖远程 `main`。
- 生产版本使用 `production/vX.Y.Z` 分支。
- 正式 tag 必须在 `scripts/final_production_acceptance.ps1 -RunFullE2E` 全绿后创建/推送。
- release notes 必须保留 reconstructed history 说明。

---

*最后更新：2026-06-06*
