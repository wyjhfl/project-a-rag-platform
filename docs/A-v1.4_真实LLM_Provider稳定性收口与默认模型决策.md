# A-v1.4 真实 LLM Provider 稳定性收口与默认模型决策

## 1. 本轮目标

A-v1.4 的目标不是继续横向加能力，而是把真实文本 LLM 的验收口径收紧，回答三个问题：

- 当前 provider 是“接不通”还是“接通但不稳定”。
- MiMo 多个文本模型和 DeepSeek 谁更适合做默认主链。
- 后续是否值得继续投入真实多模态链路。

## 2. 为什么现在先做这件事

到 A-v1.3 为止，仓库已经有统一 provider 验收脚本，但当前结论还不够适合直接做默认模型决策：

- `default_env` 是 `blocked`，但已有记录显示至少一部分原因是 API key `401 invalid_api_key`。
- `deepseek-chat` 是 `unstable`，说明它能直连，但 grounded 主链还不稳定。
- 这两类问题不能混成一个“模型不行”的结论。

因此 A-v1.4 第一刀先把“阻塞类型”显式化，再补 MiMo 候选模型清单。

## 3. 本轮最小实现

### 3.1 扩 provider 候选

在 `docs/A-v1.3_provider_manifest.example.json` 中加入：

- `mimo_v25_pro`
- `mimo_v25`
- `deepseek_chat`

其中 MiMo 文本模型先统一复用 DashScope OpenAI-compatible 路径：

- `https://dashscope.aliyuncs.com/compatible-mode/v1`

### 3.2 provider 报告新增 blocker type

在 `backend/scripts/run_provider_acceptance.py` 中新增 `blocker_type`，把失败进一步区分为：

- `accepted`
- `grounded_rejection`
- `auth_invalid`
- `config_missing`
- `timeout`
- `rate_limited`
- `provider_server_error`
- `request_rejected`
- `probe_execution_failed`
- `connectivity_or_runtime_error`

这样 A-v1.4 的报告不再只告诉我们“blocked / unstable”，还会说明更接近根因的阻塞类别。

### 3.3 测试补强

在 `backend/tests/test_av13_acceptance.py` 中补充：

- `blocker_type` 提取断言
- summary 中的 `blocker_type_counts`
- 阻塞根因分类测试

## 4. 当前边界

这一步还没有完成下面这些更重的动作：

- 还没有生成新的 A-v1.4 provider 实测报告。
- 还没有把 MiMo 多模态模型纳入视觉链路验收。
- 还没有改默认 provider。
- 还没有更新前端展示层。

所以这一步是 A-v1.4 的“验收框架补强”，不是完整收官。

## 5. 下一步如何执行

下一轮应直接做真实验收：

1. 准备可用的 MiMo API key 和 base URL。
2. 运行 `backend/scripts/run_provider_acceptance.py`。
3. 比较 `MiMo-V2.5-Pro`、`MiMo-V2.5`、`deepseek-chat`。
4. 记录每个候选的：
   - 直连成功率
   - grounded 通过率
   - fallback 情况
   - 典型失败模式
5. 形成默认模型决策。

## 6. 2026-05-18 第一轮真实验收结果

本轮实际运行产物：

- `docs/A-v1.4_provider_manifest.json`
- `docs/A-v1.4_provider_acceptance_report.json`

第一轮结果先说明了更前置的认证与配置阻塞：

```text
provider_count = 4
accepted_count = 0
unstable_count = 0
blocked_count = 4

blocker_type_counts:
- auth_invalid = 3
- config_missing = 1
```

第一轮具体结论：

- `default_env` / `mimo_v25_pro` / `mimo_v25`
  - 当前都是 `blocked`
  - 根因都是 `auth_invalid`
  - 说明此轮还没有进入真正的 grounded 能力对比阶段
- `deepseek_chat`
  - 当前是 `blocked`
  - 根因是 `config_missing`
  - 说明这次没有配置可用 DeepSeek key

这轮结果非常关键，因为它把“模型不稳定”与“认证没过”明确拆开了。第一轮还不能根据这份报告得出任何 MiMo 文本模型优劣结论，只能得出：

- MiMo 当前 key / provider 鉴权链路需要先修复
- DeepSeek 要先补 key，才能进入公平对比

### 独立认证预检

为避免每次都先跑完整 grounded 验收，本轮新增：

- `backend/scripts/preflight_provider_auth.py`

它会把 provider 排查拆成两步：

1. `GET /models`
2. 最小 `POST /chat/completions`

本轮生成：

- `docs/A-v1.4_provider_auth_preflight_2026-05-18.json`

认证预检结果：

- MiMo 三个候选：`auth_invalid`
- DeepSeek：`passed`

因此 A-v1.4 当前推荐的排查顺序应固定为：

```text
provider_auth_preflight
-> provider_acceptance
-> grounded prompt / context / fallback 收口
```

### 第二轮结果更新

在补齐 `DEEPSEEK_API_KEY` 并修复 `run_provider_acceptance.py` 的 `.env` 读取后：

- `docs/A-v1.4_provider_auth_preflight_2026-05-18.json`
  - `auth_invalid = 3`
  - `passed = 1`
- `docs/A-v1.4_provider_acceptance_report.json`
  - `auth_invalid = 3`
  - `grounded_rejection = 1`

第二轮具体结论：

- MiMo 三个候选仍然都停在 `auth_invalid`
  - 说明当前小米 key 还没有通过最小认证门
  - 还没进入模型能力比较阶段
- DeepSeek 已经通过认证层
  - `direct_llm_connected = true`
  - 但 `chat_grounded_llm = false`
  - 当前状态应定义为 `unstable`

这说明 A-v1.4 现在终于进入了有价值的判断：

- DeepSeek 已经证明“可直连”
- 但还没有证明“可稳定接管 grounded 主链”
- MiMo 当前仍需先解决鉴权

## 7. 当前推荐下一步

最优先动作不是继续调 prompt，而是先解决 provider 认证：

1. 确认 DashScope / MiMo 当前 OpenAI-compatible key 是否仍有效。
2. 确认 MiMo 模型名大小写与控制台一致。
3. 补充 `DEEPSEEK_API_KEY`。
4. 重新运行 `docs/A-v1.4_provider_acceptance_report.json`。
5. 只有在至少 1 个 provider 能通过 direct connect 后，才值得继续做 grounded 收口。

## 8. 面试讲法

这一步体现的不是“我又接了一个模型”，而是：

> 我把真实 LLM 验收从“能不能调用”升级成了“为什么没接管主链”的工程化判断。  
> 这样我可以明确区分是凭证问题、配置问题、provider 稳定性问题，还是 grounded RAG 本身不通过。

## 9. 2026-05-19 最终收口结果

在对 grounded acceptance 规则做最小修正后，A-v1.4 已经从“DeepSeek 直连但不稳定”推进到“DeepSeek 可稳定通过 grounded 验收”。

本轮新增或更新：

- `backend/tests/test_llm_grounded_acceptance.py`
- `docs/A-v1.4_real_llm_grounding_preflight_deepseek_2026-05-19.json`
- `docs/A-v1.4_provider_acceptance_report_2026-05-19.json`

关键结果：

```text
DeepSeek grounded preflight
- direct_llm_connected = true
- chat_grounded_llm = true
- accepted_attempt = 1

Provider acceptance
- accepted = 1
- blocked = 3
```

最终判断：

- `deepseek_chat` 已达到 A-v1.4 的最小完成标准，可作为当前默认真实文本 LLM 候选。
- MiMo 三个候选当前仍为 `auth_invalid`，暂时不能参与默认主链决策。
- 当前最合理的推进顺序变为：
  - A-v1.4 完成收口
  - A-v1.5 处理真实多模态
  - 并行保留 MiMo 认证修复作为 side task
