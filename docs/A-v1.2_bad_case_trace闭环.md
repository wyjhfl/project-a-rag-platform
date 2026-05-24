# A-v1.2 bad case trace 闭环

## 1. 文档目标

这份文档不重复展示所有评测结果，只挑两类最有代表性的 case，演示 A-v1.2 新增的闭环能力：

```text
bad case
-> trace
-> 根因判断
-> 修复建议
```

## 2. Case A：`real-reg-004`

问题：

```text
A100 维护后怎么复测压力是否稳定？
```

评测结果：

```text
likely_issue = context_noise
faithfulness = 0.2
answer_relevancy = 0.0
context_precision = 0.25
context_recall = 1.0
```

现象：

- 上下文里其实已经有 `空载运行 / 带载观察 / 压力曲线`
- 但最终答案没有把这些关键词说出来
- 回答退回成了更泛化的“排查步骤”表述

trace 关键信号：

```text
security_check
query_route
hybrid_retrieval
rerank
agentic_search
answer_decision
```

从 trace 反推：

- `query_route` 没有走 query rewrite，说明系统认为这个问题不是召回困难 case。
- `hybrid_retrieval` 和 `rerank` 已经把 A100 相关 chunk 召回进来了。
- `context_recall = 1.0` 证明期待关键词都在上下文里。

根因判断：

这类问题不是“没检到”，而是：

```text
上下文有了
但答案没有把复测动作总结出来
```

也就是典型的：

```text
context_noise + answer extraction 不够聚焦
```

修复建议：

- 对“复测 / 验证 / 如何确认恢复正常”这类问题增加回答模板。
- 在生成前对命中的关键词做二次聚焦，把复测动作优先提到回答前部。
- 如果问题是“怎么确认稳定”，优先抽取带步骤和验证标准的 chunk，而不是通用排查 chunk。

## 3. Case B：`real-reg-008`

问题：

```text
UPS-30K 机房温度高导致过温时是否建议强制重启？
```

评测结果：

```text
likely_issue = answer_coverage_gap
faithfulness = 0.375
answer_relevancy = 0.3333
context_precision = 0.5
context_recall = 1.0
```

现象：

- 上下文里已经有 `机房温度 / 过温 / 不建议`
- 最终答案确实补了安全后处理
- 但 `expected_keywords` 中的 `过温 / 不建议` 没有被回答正文稳定覆盖

trace 关键信号：

```text
query_route
hybrid_retrieval
rerank
agentic_search
answer_decision
```

从 trace 反推：

- 系统能命中 `real_ups_30k_thermal.md` 和 `real_ups_30k_safety.md`
- `answer_decision` 显示 `safety_warning=true`
- 这说明安全后处理已经介入，但回答正文仍偏“检索摘要 + 通用安全补充”

根因判断：

这类问题不是“没有安全边界”，而是：

```text
安全边界存在
但回答没有稳定把“是否建议强制重启”的判断说成更直接的话
```

所以它更接近：

```text
answer_coverage_gap
```

修复建议：

- 对 `是否可以 / 是否建议 / 能不能继续运行` 这类二元判断问题，优先在答案首句给出结论。
- 保留安全后处理，但不要只依赖后置安全模板表达风险。
- 在生成阶段增加“先回答结论，再给检查项”的结构化约束。

## 4. A-v1.2 闭环价值

这两个 case 体现了 A-v1.2 的核心变化：

- 以前只能看到分数低。
- 现在能看到：
  - 问题是召回没到，还是上下文脏。
  - 是答案没说全，还是安全判断没前置。
  - trace 节点里每一步发生了什么。

这让 bad case 不再只是记录现象，而是成为下一轮优化的明确输入。
