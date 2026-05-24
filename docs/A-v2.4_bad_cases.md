# A-v2.4 Bad Cases：Provider 对比

## BC-A-v2.4-001：MiMo v2.5 Pro 在 A100 E-17 case 中 fallback

现象：

```text
provider = mimo_token_plan_v25_pro
case = provider-001
llm_used = false
expected_hit_count = 4 / 4
citation_count = 3
```

说明：

- 检索和引用是有效的。
- 期望词全部命中。
- 但真实 LLM 输出没有被 grounded acceptance 接受，最终回退到本地 extractive generator。

影响：

- `mimo_token_plan_v25_pro` 当前不建议作为默认演示主链。
- 它可以作为候选 provider，但需要继续观察稳定性。

## BC-A-v2.4-002：MiMo v2.5 Pro 平均延迟偏高

现象：

```text
mimo_token_plan_v25_pro avg_latency_ms = 14000.83
mimo_token_plan_v25 avg_latency_ms = 5608.27
deepseek_chat avg_latency_ms = 1801.12
```

影响：

- 现场 demo 对响应速度敏感。
- 即使 provider 能转绿，延迟也会影响默认链路选择。

结论：

- `deepseek_chat` 继续作为默认公开 demo provider。
- `mimo_token_plan_v25` 作为候选 provider 和对比亮点。
- `mimo_token_plan_v25_pro` 暂不进入默认路径。
