# A-v2.4 Provider 对比报告复盘

## 阶段 1：技术知识教学

A-v2.4 解决的问题是：在 A-v2.2 已确认 MiMo 和 DeepSeek 都能通过 grounded 验收后，进一步回答“哪个 provider 更适合作为默认演示主链，哪个更适合作为候选对照”。

这不是重新做 RAG 评测，而是 provider 层的横向对比。

核心技术点：

- **Grounded 接管率**：同一组问题下，真实 LLM 是否被主链接受为最终回答。
- **引用覆盖率**：回答是否仍带有有效 citations。
- **期望词命中率**：答案和引用是否覆盖设备型号、故障码、部件、安全动作等关键词。
- **估算 token**：使用本地 `TokenCostEstimator` 做相对成本比较，不冒充供应商账单。
- **延迟**：记录端到端 `/chat` 调用耗时，反映演示体验。
- **warning 继承**：沿用 A-v2.2 provider acceptance 中的 warnings，避免忽略 direct smoke 行为差异。

如果只看“是否 accepted”，三个候选都能转绿；但演示和默认主链需要进一步看稳定性、速度和成本。

## 阶段 2：版本技术设计

### 本轮目标

- 复用 A-v2.2 provider manifest。
- 跳过 `default_env`，只比较明确候选 provider。
- 跑 3 个真实售后诊断 case。
- 输出 provider 排名和逐 case 证据。

### 本轮边界

不做：

- 不新增 RAG 能力。
- 不改默认 demo provider。
- 不调用外部价格 API。
- 不把估算 token 当真实账单。

只做：

- 横向对比 DeepSeek 和 MiMo。
- 记录真实运行结果。
- 给出默认主链建议。

### 涉及文件

- `backend/scripts/run_av24_provider_comparison.py`
- `backend/tests/test_av24_provider_comparison.py`
- `docs/A-v2.4_provider_comparison_report_2026-05-23.json`
- `docs/A-v2.4-provider-comparison-review.md`
- `docs/A-v2.4_bad_cases.md`
- `README.md`
- `docs/dev_log.md`
- `docs/debug_log.md`

## 阶段 3：真实运行结果

命令：

```powershell
python backend/scripts/run_av24_provider_comparison.py `
  --manifest docs/A-v2.2_provider_manifest.json `
  --acceptance-report docs/A-v2.2_provider_acceptance_report_2026-05-23.json `
  --output docs/A-v2.4_provider_comparison_report_2026-05-23.json `
  --dotenv-override
```

结果摘要：

```text
provider_count = 3
case_count = 3
```

排名：

```text
1. mimo_token_plan_v25
   llm_used_rate = 1.0
   expected_hit_rate = 0.9167
   avg_estimated_tokens = 184.0
   avg_latency_ms = 5608.27

2. deepseek_chat
   llm_used_rate = 1.0
   expected_hit_rate = 0.9167
   avg_estimated_tokens = 225.67
   avg_latency_ms = 1801.12

3. mimo_token_plan_v25_pro
   llm_used_rate = 0.6667
   expected_hit_rate = 1.0
   avg_estimated_tokens = 202.67
   avg_latency_ms = 14000.83
```

## 阶段 4：复盘总结

结论：

- `deepseek_chat` 仍推荐作为公开 demo 默认主链。
- `mimo_token_plan_v25` 已具备 grounded 可比较状态，适合作为候选 provider 和对比亮点。
- `mimo_token_plan_v25_pro` 当前不建议作为默认演示主链，因为 3 个 case 中有 1 个 fallback，且平均延迟最高。

为什么 DeepSeek 仍保留默认：

- 3/3 grounded 接管。
- 3/3 有引用。
- 期望词命中率与 MiMo v2.5 持平。
- 平均延迟显著更低，演示体验更稳。

为什么 MiMo v2.5 值得讲：

- A-v2.2 已从认证阻塞转绿。
- A-v2.4 中 3/3 grounded 接管。
- 估算 token 更低。
- 可以作为 provider 多样性和国产模型接入能力的展示点。

面试讲法：

> 我没有只停留在“provider 接通”，而是把 DeepSeek 和 MiMo 放到同一组售后诊断 case 上横向比较。最终 DeepSeek 仍保留为公开 demo 默认主链，因为它 grounded 接管率、引用覆盖和延迟表现更适合现场演示；MiMo v2.5 已经从认证阻塞推进到可比较候选，可以作为 provider 多样性的证据。MiMo v2.5 Pro 当前有一次 fallback 和更高延迟，所以不作为默认。

## 验证

```text
python -m pytest backend/tests/test_av24_provider_comparison.py -q
2 passed

python -m compileall backend\scripts\run_av24_provider_comparison.py
passed
```

## 下一步

推荐进入 A-v2.5 演示素材补强：

- 补 README 截图索引。
- 补演示中心截图清单。
- 补 5 分钟讲解路线。
- 可选生成公开作品集 checklist。
