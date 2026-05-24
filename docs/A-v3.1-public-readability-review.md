# A-v3.1 公开展示与面试讲法收口

## 本轮目标

把 A-v2.9 的评测质量提升和 A-v3.0 的公开发布结果，整理成招聘方首次打开仓库时能快速理解的表达。

本轮不新增业务功能，不改 RAG 主链，只优化公开入口和面试讲法。

## 公开阅读路径

推荐阅读顺序：

```text
README 30 秒看懂项目
-> 当前状态
-> 快速启动 Demo
-> 证据索引
-> docs/interview_pitch_pack.md
-> docs/final_delivery_index.md
```

这样可以先回答三个问题：

- 这个项目解决什么业务问题。
- 它和普通聊天 demo 的区别是什么。
- 有哪些真实验收证据证明质量提升。

## 本轮改动

- `README.md`
  - 新增 “30 秒看懂项目”。
  - 将当前阶段更新为 A-v3.1。
  - 把真实回归、真实对抗和 RAGAS 风格指标前置。
  - 将下一步从面试讲法更新切到远端 CI 与公开展示复核。
- `docs/interview_pitch_pack.md`
  - 在 2 分钟、5 分钟和 15 分钟讲法中补入 A-v2.9 指标。
  - 强化“幻觉缓解、拒答边界、跨设备过滤、危险操作升级”的表达。
- `docs/final_delivery_index.md`
  - 新增 A-v3.1 作为公开展示与面试讲法证据入口。
- `backend/scripts/create_public_release_repo.py`
  - 将 A-v3.1 文档纳入公开发布包。

## 当前可讲结论

Project A 当前可以这样概括：

> 这是一个设备售后诊断 RAG 工程系统。它不只回答问题，还把检索、引用、grounded 校验、评测、bad case、trace、Provider 验收、多模态边界和工单升级组织成可验收闭环。

质量提升证据：

```text
real regression: 30/30
real adversarial: 20/20
context_precision: 0.8667
faithfulness: 0.6983
context_recall: 0.9778
```

幻觉缓解证据：

- 未知型号直接拒答，不套用 UPS / CW200 / VFD 等相似资料。
- 缺少型号或故障码时要求补充信息，不编造排障结论。
- 跨设备相似故障通过设备、故障码和意图约束过滤。
- 危险操作必须输出禁止/不建议、停机/隔离和人工确认。

## 验收方式

本轮主要是文档与发布包整理，验证重点是链接、导出和 Markdown 可读性：

```powershell
python backend/scripts/create_public_release_repo.py --target tmp/public-release-check-v31 --force
```

预期结果：

- README 能在首屏说明业务场景、默认 demo、质量指标和证据入口。
- A-v3.1 文档进入公开发布包。
- 最终交付索引能跳转到 A-v3.1 复盘。

## 面试讲法

推荐收束句：

> 我把 RAG 项目从“能回答”推进到了“能证明回答质量、能解释失败边界、能本地演示验收状态”的工程状态。A-v2.9 后，真实回归从 20 条扩到 30 条并 30/30 通过，对抗样本从 10 条扩到 20 条并 20/20 通过，同时把未知型号、资料不足、跨设备混淆和危险操作都纳入了幻觉缓解测试。

## 下一步

A-v3.2 建议做远端展示复核：

- 检查 GitHub Actions 是否通过。
- 检查 README 链接是否全部可打开。
- 检查公开仓库首屏是否足够清晰。
- 如 CI 有失败，优先修 CI，而不是继续扩功能。
