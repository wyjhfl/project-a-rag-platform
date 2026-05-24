# A-v1.2 评测与可观测性说明

## 1. 本轮目标

A-v1.2 不扩 RAG 业务功能，重点把 Project A 从“有评测脚本、有 trace hook”升级为：

- 有更可解释的评测报告
- 有本地可复现的 trace 主链
- 有 bad case 到 trace 的闭环分析入口

## 2. 这次具体做了什么

### 2.1 升级 `evaluate_ragas.py`

原来的脚本只有四个平均分：

- `faithfulness`
- `answer_relevancy`
- `context_precision`
- `context_recall`

A-v1.2 补了三层内容：

- case 级 `diagnostics`
  - `answer_keyword_hits / misses`
  - `context_keyword_hits / misses`
  - `citation_count / context_count`
  - `trace_event_names`
  - `agentic_quality_score / retried / rewritten_query`
- summary 级问题归因
  - `issue_counts`
  - `low_score_case_count`
  - `low_score_cases`
- trace 嵌入
  - 每个 case 报告里直接保留本次问答的 trace 快照

### 2.2 升级 tracing 主链

原来的 `backend/app/rag/tracing.py` 只是一个轻量 LangSmith decorator 包装。  
A-v1.2 增加了本地 trace session，默认不依赖外部平台也能记录关键链路。

当前默认 trace 节点：

```text
security_check
query_route
hybrid_retrieval
rerank
agentic_search
answer_decision
```

这意味着现在一次 case 不只是“得了多少分”，还能看到：

- query 被路由成了什么检索模式
- hybrid 检索召回了哪些 chunk
- rerank 后前几条变成了什么
- agentic retrieval 有没有重写 query
- 最终 citations 和 llm_used 是什么

### 2.3 让评测和 trace 真正连起来

现在 `docs/A-v1.2_ragas_report.json` 中每条结果都同时包含：

- `scores`
- `diagnostics`
- `trace`

这就是 A-v1.2 的核心价值：

```text
不是只有分数
而是能从分数反推到链路
```

## 3. 本轮真实结果

评测命令：

```powershell
python backend/scripts/evaluate_ragas.py --cases data/eval/real_regression_cases_v1.json --docs-dir data/real_manuals_sanitized --output docs/A-v1.2_ragas_report.json
```

在公开主链口径下得到：

```text
case_count: 20
faithfulness: 0.415
answer_relevancy: 0.6333
context_precision: 0.5375
context_recall: 0.85
source_hit_count: 20 / 20
```

问题归因分布：

```text
grounding_gap: 9
context_noise: 8
answer_coverage_gap: 2
pass_or_minor_gap: 1
```

## 4. 这些结果怎么解读

### 4.1 `source_hit_count=20/20`

说明这批真实资料回归集里，目标资料源基本都能召回到。  
这代表“有没有找到对的文档”这一步不算当前最主要短板。

### 4.2 `context_precision=0.5375`

说明当前更突出的短板仍然是上下文噪声。  
也就是：系统常常能找到相关资料，但给生成层的上下文还不够干净。

### 4.3 `faithfulness=0.415`

说明答案和上下文的词项重合度仍偏低。  
在当前实现里，这通常不是“完全幻觉”，更常见的是：

- 生成表达被压缩改写
- 抽取式答案只取了上下文部分句子
- 回答没有把 case 期待关键词说全

### 4.4 `answer_relevancy=0.6333`

说明大多数问题能回答到方向，但答案覆盖还不稳定。  
也就是：系统常常“答对方向”，但不总是“把关键检查项讲全”。

## 5. A-v1.2 的工程价值

这一版最重要的不是分数涨了多少，而是项目终于具备了下面这套分析链：

```text
case
-> score
-> diagnostics
-> trace
-> likely_issue
```

这让 Project A 从：

```text
能跑一次的评测脚本
```

升级到：

```text
能解释失败、能定位链路、能指导下一轮优化的评测体系
```

## 6. 当前边界

A-v1.2 仍然没有做这些更重的事情：

- 没有接完整官方 `ragas` 包和外部 judge LLM 体系
- 没有做 LangSmith / LangFuse 双平台统一展示
- 没有做前端 trace 可视化
- 没有把 bad case 自动回写数据库或追踪系统

这些不影响 A-v1.2 的最小目标，因为这一版重点是先把“可解释评测 + 本地 trace + bad case 闭环”做实。
