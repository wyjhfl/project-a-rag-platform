# A-v2.6 Bad Cases

## 范围

A-v2.6 是公开交付检查，不新增业务能力。

本轮 bad case 只记录交付和演示风险，不记录新的 RAG 答案质量问题。

## Case 1：公开导出脚本证据清单滞后

现象：

`backend/scripts/create_public_release_repo.py` 仍主要复制 v1.x 材料，缺少 A-v2.2 到 A-v2.6 的核心验收报告、demo 文档、截图和启停脚本。

影响：

- 公开导出包会缺少 MiMo 重新验收、PaddleOCR 兼容性边界、Provider 对比和最终交付索引。
- README 中能看到新结论，但导出包里找不到对应证据。

处理：

- 将 A-v2.2 到 A-v2.6 核心 docs 加入导出清单。
- 将 `.env.demo.example` 和 demo 启停脚本加入导出清单。
- 将 A-v2.5 截图目录加入导出清单。

结论：

该问题属于交付材料遗漏，不影响主仓库 demo 运行。

## Case 2：面试讲法仍保留旧 MiMo 口径

现象：

`docs/interview_guide.md` 中仍将 MiMo 描述为认证 / 接入层没转绿。

影响：

这与 A-v2.2 / A-v2.4 结论冲突，面试时容易讲错状态。

处理：

- 更新为：MiMo token-plan 已通过 grounded 重新验收。
- `mimo-v2.5` 作为候选 provider 对照。
- 默认公开 demo 仍使用 `deepseek_chat`。

结论：

这是文档口径滞后，不是 provider 能力回退。
