# Release Lineage Notice

## 概述

当前仓库的 Git 历史经历了 `.git` 目录损毁和重建，**不是原始的连续提交历史**。任何基于此仓库的 release 都必须明确此风险。

## 事件经过

1. **原始历史**：项目曾拥有完整的 Git 历史，包含原始 v1.0.0 tag（commit `e64b095`）。
2. **`.git` 损毁**：在执行 `git checkout` 操作时，`.git` 目录被损坏（Git 在当前系统上的已知问题），导致所有历史丢失。
3. **仓库重建**：通过 `git init` 重新初始化仓库，并逐次提交恢复的代码。
4. **v1.0.0 重建**：创建了 reconstructed v1.0.0 tag（commit `111066c`），但此 tag 不是原始的 `e64b095`。

## 当前历史链

```
c2afe65  fix: restore backend test coverage and production acceptance confidence
8f07973  fix: recover production acceptance consistency
43d700d  Redis rate limit + worker stress
111066c  (tag: v1.0.0) reconstructed v1.0.0
```

**关键事实**：
- `111066c` 是重建的 v1.0.0 tag，不是原始 `e64b095`
- 原始 `e64b095` 不在当前本地历史中
- 远程 `origin`（`https://github.com/wyjhfl/project-a-rag-platform.git`）是不同的代码库（作品集交付版 A-v3.5），不包含原始工程化版本的历史

## 远程仓库状态

| 属性 | 值 |
|---|---|
| Remote URL | `https://github.com/wyjhfl/project-a-rag-platform.git` |
| 远程代码库性质 | 作品集交付版（A-v3.5） |
| 远程 tags | `v1.0-public`, `v1.1-public`, `v1.2-public`, `v3.5-public-delivery` |
| 是否包含 v1.0.0 | 否 |
| 是否包含 e64b095 | 否 |
| 是否可用于恢复原始历史 | 否 |

## 后续选择

### 选项 A：接受 Reconstructed History 并继续 Release

- 将当前仓库作为 canonical repo
- 从 v1.0.1 起管理新的 release lineage
- 在所有 release notes 中注明 "based on reconstructed history"
- 优点：立即可用，无需额外操作
- 缺点：历史不可信，无法验证 v1.0.0 之前的变更

### 选项 B：从可信备份恢复原始历史

- 如果存在包含原始 `.git` 目录的备份
- 将备份恢复后，cherry-pick 或 reapply 当前变更
- 优点：恢复可信历史
- 缺点：需要找到可信备份源

### 选项 C：将当前仓库作为新 Canonical Repo

- 正式声明 v1.0.0 (reconstructed) 为新起点
- 删除旧的 v1.0.0 tag，创建新的 v1.0.0-reconstructed tag
- 从 v1.0.1 起使用新的 tag 命名规范
- 优点：语义清晰，不伪装为原始历史
- 缺点：与任何外部引用的 v1.0.0 不兼容

## 建议

在做出选择之前，**不建议创建正式 v1.0.1 release tag**。RC tag（如 `v1.0.1-rc.1`）可以创建，但必须注明此 lineage notice。

---

*文档创建日期：2026-06-05*
*最后更新：2026-06-05*
