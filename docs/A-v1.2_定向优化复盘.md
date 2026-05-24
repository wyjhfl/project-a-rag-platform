# A-v1.2 定向优化复盘

## 1. 本轮目标

A-v1.2 第一轮评测后，主要问题集中在两类：

- `context_noise`：召回里已经有对的资料，但回答引用混入了同设备其他故障或其他设备的通用排查段落。
- `grounding_gap`：本地 fallback 生成器只是顺序拼句，没有优先把和问题最对齐的句子抽出来。

这轮不扩功能，只做定向优化，目标是压低噪音 citation，提高回答对 expected keywords 的覆盖。

## 2. 实际改动

### 2.1 统一相关性评分

新增并复用统一的 chunk 相关性口径：

- 文件：`backend/app/rag/scoring.py`
- 能力：
  - 统一 token 化
  - 提取设备型号
  - 提取真正的故障码
  - 计算 chunk 对问题的相关性分数
  - 加入设备匹配、故障码匹配、意图词 bonus

这里的关键不是“分更复杂”，而是让 rerank、生成前过滤、回答抽句都基于同一套判断标准。

### 2.2 收紧本地 rerank

文件：`backend/app/rag/reranker.py`

本地 reranker 从“词重合 + 数字 bonus”升级为直接使用统一相关性评分。

结果是：

- 同设备且故障码完全一致的 chunk 会更稳定排到前面。
- 同设备但不同故障码的 chunk 不再轻易挤进前几名。

### 2.3 生成前做上下文聚焦

文件：`backend/app/rag/pipeline.py`

新增 `answer_context_filter` 阶段，做两件事：

- 先按统一相关性评分截取更聚焦的 answer chunks。
- 如果问题里有显式故障码，优先只保留命中该故障码的 chunks。

这样回答和 citations 不再机械复用全部 top_k 结果，而是只保留最应该进入最终回答的那一小部分上下文。

### 2.4 改进本地 fallback 生成器

文件：`backend/app/rag/generator.py`

本地生成器从“按 chunk 顺序摘前 4 句”改成：

- 先根据问题类型生成一句结论性开头
- 再对句子做相关性打分
- 优先抽取和问题最对齐的句子

这一步主要改善的是：

- “是否建议/可不可以”类问题先给结论
- “复测/确认/稳定”类问题优先给复测动作
- “备件/部件”类问题优先给部件和检查点

### 2.5 收紧 Agentic 质量判断

文件：`backend/app/rag/agentic.py`

`quality_score` 原来使用的 token 规则对中文症状表达偏弱，容易把已经检到正确 chunk 的 case 误判成资料不足。

这轮改成复用新版 token 化口径，并把 source 也纳入质量判断文本。

直接修掉了两类误判：

- `CW200 出水温度降不下来应该检查什么？`
- `VFD-4500 欠压 UV-1 需要检查哪些供电项？`

## 3. 真实结果

本轮重新生成：

- `docs/A-v1.2_ragas_report.json`

优化前：

```text
faithfulness: 0.415
answer_relevancy: 0.6333
context_precision: 0.5375
context_recall: 0.85
low_score_case_count: 19
source_hit_count: 20 / 20
```

优化后：

```text
faithfulness: 0.4384
answer_relevancy: 0.8667
context_precision: 0.775
context_recall: 0.8833
low_score_case_count: 12
source_hit_count: 20 / 20
```

最有价值的变化不是平均分本身，而是：

- `context_noise` 不再是主导问题
- `source_hit_count` 没有因为过滤而掉下来
- 低分 case 从 19 个降到 12 个

## 4. 当前剩余问题

现在最主要的问题已经收敛成 `grounding_gap`。

这说明：

- 检索和引用比之前干净了
- 但本地 extractive answer 仍然不够“工程化表达”

换句话说，下一轮最值得打的不是继续压 retrieval，而是：

- 让 fallback 生成器更稳定地输出“结论 -> 依据 -> 动作”
- 或者在真实 LLM 可用时，把这套结构约束前移到 prompt / post-process

## 5. 面试怎么讲

这一轮非常适合讲“我不是只会看平均分，而是会根据评测结果做定向优化”：

```text
先用 A-v1.2 的 case 级评测和 trace 找到主要问题
-> 判断主要不是召回缺失，而是上下文噪音和答案抽取不聚焦
-> 用最小改动同时修正 rerank、answer context filter 和 fallback generator
-> 再用同一套真实 case 复跑，验证指标变化
```

这比单纯说“我做了 RAGAS 和 LangSmith”更有工程说服力。
