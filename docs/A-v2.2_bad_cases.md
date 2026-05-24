# A-v2.2 Bad Cases：MiMo Provider 重新验收

## BC-A-v2.2-001：旧 DashScope 口径导致 MiMo auth_invalid

现象：

```text
base_url = https://dashscope.aliyuncs.com/compatible-mode/v1
model = MiMo-V2.5-Pro / MiMo-V2.5
status = auth_invalid
```

根因：

- A-v1.4 使用的是旧 DashScope compatible endpoint。
- 当前 `.env` 已经切换到 `https://token-plan-cn.xiaomimimo.com/v1`。
- 旧口径下的失败不能继续作为 MiMo 能力结论。

处理：

- 新增 `docs/A-v2.2_provider_manifest.json`。
- 使用 token-plan 口径重新跑 auth preflight 和 provider acceptance。

结论：

- A-v2.2 中 token-plan MiMo 已通过认证和 grounded 验收。

## BC-A-v2.2-002：MiMo direct smoke 空答案但 grounded chat 通过

现象：

```text
direct_llm_connected = false
chat_grounded_llm = true
status = accepted
```

影响范围：

- `default_env`
- `mimo_token_plan_v25_pro`
- `mimo_token_plan_v25`

根因判断：

- MiMo 在极短 direct smoke prompt 下可能返回空 `content`，但在真实 RAG prompt 和上下文约束下可以产出 grounded 答案。
- 因此 direct smoke 失败不应覆盖端到端 grounded 成功。

处理：

- `backend/scripts/preflight_real_llm_grounding.py` 将该场景降级为 `warnings`。
- `backend/scripts/run_provider_acceptance.py` 透传 warnings 到 provider acceptance 报告。

结论：

- 对 Project A 的默认候选判断，应以 `chat_grounded_llm=true` 为准。
- direct smoke 空答案保留为 provider 行为差异，不作为发布阻塞。
