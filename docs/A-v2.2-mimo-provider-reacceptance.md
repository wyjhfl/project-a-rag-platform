# A-v2.2 MiMo Provider 重新验收

## 阶段 1：技术知识教学

A-v2.2 解决的问题不是“再接一个模型”，而是把 MiMo 从旧的认证阻塞状态推进到可判断的真实 provider 状态。

A-v1.4 的 MiMo 阻塞发生在旧口径：

```text
base_url = https://dashscope.aliyuncs.com/compatible-mode/v1
model = MiMo-V2.5-Pro / MiMo-V2.5
status = auth_invalid
```

当前 `.env` 已经切到新的 token-plan 口径：

```text
LLM_PROVIDER = xiaomi_mimo
LLM_MODEL = mimo-v2.5-pro
LLM_BASE_URL = https://token-plan-cn.xiaomimimo.com/v1
```

因此本轮必须先重新验收认证层，再判断 grounded 能力。

核心技术点：

- **Auth preflight**：只验证 `/models` 和最小 `/chat/completions`，用于判断 key、base_url、model id 是否可用。
- **Provider acceptance**：走真实 RAG grounded 链路，验证 provider 是否能产出被项目接受的回答。
- **Blocker type**：把失败拆成 `auth_invalid`、`config_missing`、`model_or_request_rejected`、`grounded_rejection` 等，而不是笼统说失败。
- **默认候选决策**：只有 `chat_grounded_llm=true` 的 provider 才能进入默认文本主链候选。

如果不这样拆，会把“key 错了”“endpoint 错了”“模型名错了”“回答不 grounded”混成一个失败结论，面试和后续优化都讲不清。

## 阶段 2：版本技术设计

### 本轮目标

- 新增 A-v2.2 专用 provider manifest。
- 用 token-plan 口径重新验收 MiMo。
- 跑 auth preflight。
- 跑 provider acceptance。
- 写入真实报告和版本复盘。

### 本轮边界

不做：

- 不改 RAG 主链。
- 不改 LLMGenerator。
- 不切换默认 demo provider。
- 不承诺 MiMo 一定转绿。
- 不做多模态 OCR / MinerU / PaddleOCR。

只做：

- provider 配置口径更新。
- provider 认证与 grounded 验收。
- 结果记录和边界说明。

### 涉及文件

- `docs/A-v2.2_provider_manifest.json`
- `docs/A-v2.2_provider_auth_preflight_2026-05-23.json`
- `docs/A-v2.2_provider_acceptance_report_2026-05-23.json`
- `docs/A-v2.2-mimo-provider-reacceptance.md`
- `docs/dev_log.md`
- `docs/debug_log.md`
- `README.md`

### 验收命令

```powershell
python backend/scripts/preflight_provider_auth.py `
  --manifest docs/A-v2.2_provider_manifest.json `
  --output docs/A-v2.2_provider_auth_preflight_2026-05-23.json
```

```powershell
python backend/scripts/run_provider_acceptance.py `
  --manifest docs/A-v2.2_provider_manifest.json `
  --output docs/A-v2.2_provider_acceptance_report_2026-05-23.json `
  --version A-v2.2
```

### 验收标准

- auth preflight 能区分 MiMo 是认证通过、模型拒绝、配置缺失还是连接失败。
- provider acceptance 能说明 MiMo 是否进入 grounded 能力比较。
- DeepSeek 继续作为对照组。
- 结果写入文档，不只停留在终端输出。

## 阶段 3：真实运行结果

### Auth preflight

命令：

```powershell
python backend/scripts/preflight_provider_auth.py `
  --manifest docs/A-v2.2_provider_manifest.json `
  --output docs/A-v2.2_provider_auth_preflight_2026-05-23.json `
  --dotenv-override
```

结果：

```text
provider_count = 4
passed = 4
```

结论：

- 当前 token-plan 口径下，MiMo 已经不再卡认证层。
- `/models` 可返回 `mimo-v2.5-pro` 和 `mimo-v2.5`。
- 最小 `/chat/completions` 请求可返回 200。

### Provider acceptance

命令：

```powershell
python backend/scripts/run_provider_acceptance.py `
  --manifest docs/A-v2.2_provider_manifest.json `
  --output docs/A-v2.2_provider_acceptance_report_2026-05-23.json `
  --version A-v2.2 `
  --dotenv-override
```

结果：

```text
provider_count = 4
accepted_count = 4
unstable_count = 0
blocked_count = 0
```

通过项：

- `default_env`
- `mimo_token_plan_v25_pro`
- `mimo_token_plan_v25`
- `deepseek_chat`

注意：

- MiMo 三条路径存在 `direct_llm_connected=false` 的 warning。
- 但三条路径的 `chat_grounded_llm=true`，并且 `accepted_attempt=1`。
- 这说明 direct smoke 空答案不是 Project A grounded RAG 链路的发布阻塞。

### 工程修正

- `backend/scripts/preflight_provider_auth.py`
  - 新增 `--dotenv-override`，避免旧进程环境污染 `default_env`。
- `backend/scripts/run_provider_acceptance.py`
  - 新增 `--dotenv-override`。
  - 透传 `warnings` 字段。
- `backend/scripts/preflight_real_llm_grounding.py`
  - 当 grounded chat 已通过时，把 direct smoke 空答案降级为 warning。

### 验证

```text
python -m pytest backend/tests/test_av13_acceptance.py -q
7 passed

python -m compileall backend\scripts\preflight_real_llm_grounding.py backend\scripts\preflight_provider_auth.py backend\scripts\run_provider_acceptance.py
passed
```

## 阶段 4：复盘总结

本轮学到的关键点：

- provider 失败必须先拆认证层和 grounded 层。
- 旧 endpoint 的 `auth_invalid` 不能继续代表当前 MiMo 能力。
- direct smoke 不等于真实 RAG 主链验收。
- 对 Project A 来说，最终默认候选应优先看 `chat_grounded_llm=true`。

当前代码链路：

```text
A-v2.2_provider_manifest
-> preflight_provider_auth
-> run_provider_acceptance
-> preflight_real_llm_grounding
-> RAG ingest / chat
-> grounded acceptance
-> JSON evidence
```

面试讲法：

> A-v2.2 我把 MiMo 从“认证阻塞”重新推进到了“真实可比较 provider”。旧 DashScope 口径下 MiMo 是 auth_invalid，但切到 token-plan endpoint 后，`mimo-v2.5-pro` 和 `mimo-v2.5` 都通过了 grounded RAG 验收。这里还有一个工程细节：MiMo 在 direct smoke 下可能返回空 content，但端到端 RAG grounded 验收能通过，所以我把它记录为 warning，而不是错误地判成能力失败。

下一步：

- A-v2.3 推荐继续做 PaddleOCR 兼容性专项。
- 或者先做 A-v2.2b provider 对比报告，把 DeepSeek 与 MiMo 的回答质量、稳定性和 token 成本做横向对比。
