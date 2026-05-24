# A-v2.5 标准演示脚本

## 演示目标

用 5-10 分钟讲清 Project A 已经具备：

```text
可本地启动
-> 可前端展示
-> 可验收追溯
-> 可解释边界
-> 可面试讲全链路
```

推荐主线：

```text
业务问题
-> demo 画像
-> 验收中心
-> 文本 LLM 主链
-> Provider 对比
-> 多模态边界
-> evaluation / bad case / trace
-> 下一步规划
```

## 1. 项目定位

讲法：

> Project A 面向企业设备售后诊断场景。用户输入设备型号、故障码或现场现象后，系统从维修知识中检索证据，生成 grounded 诊断建议，并在需要时进入工单和人工升级闭环。

强调：

- 不是普通聊天 demo。
- 核心价值是“故障描述 -> 证据检索 -> 可引用回答 -> 工单闭环”。
- 每条能力都要有验收证据和边界说明。

## 2. Demo 画像

讲法：

> 当前公开演示使用 sqlite + chroma + deepseek-chat。这个画像最稳定，适合现场演示；MiMo 已完成重新验收，作为候选 provider 对比展示。

展示：

- `.env.demo.example`
- `scripts/start_demo_stack.ps1`
- `scripts/stop_demo_stack.ps1`
- `docs/demo_guide.md`

## 3. 启动和健康检查

执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_demo_stack.ps1 -StopExisting
```

展示：

- `http://127.0.0.1:18082/health`
- `http://127.0.0.1:18082/api/v1/system/status`
- `http://127.0.0.1:4175/`

讲法：

> 先确认后端、前端、LLM 画像、资料源和向量库都处在可演示状态。

## 4. 验收中心

打开：

```text
http://127.0.0.1:4175/
```

重点讲：

- Provider 状态
- 多模态状态
- evaluation 指标
- bad case 卡片
- trace 时间线
- 原始 JSON

讲法：

> 验收中心不是静态说明页，它读取仓库中的真实 JSON 和 Markdown 证据，把系统状态聚合成前端可讲的状态板。

## 5. 文本 LLM 主链

讲法：

> deepseek_chat 已通过 grounded 验收，说明它不只是能直连，而是能在检索上下文约束下生成可接受答案。

强调：

- `direct_llm_connected` 只说明能连通。
- `chat_grounded_llm` 才说明能接管 RAG 回答。
- 如果答案没有足够上下文支撑，主链会 fallback 或拒答。

证据：

- `docs/A-v1.4_provider_acceptance_report_2026-05-19.json`
- `docs/A-v1.4_real_llm_grounding_preflight_deepseek_2026-05-19.json`

## 6. Provider 对比

讲法：

> A-v2.2 把 MiMo 从旧的认证阻塞推进到 token-plan 口径下的 grounded 可比较 provider；A-v2.4 再把 DeepSeek 和 MiMo 放到同一组售后诊断 case 上横向比较。

结论：

- `deepseek_chat`：默认公开 demo 主链，延迟最低，现场演示最稳。
- `mimo_token_plan_v25`：候选 provider，3/3 grounded 接管，估算 token 更低。
- `mimo_token_plan_v25_pro`：暂不进默认路径，有一次 fallback，平均延迟最高。

证据：

- `docs/A-v2.2_provider_acceptance_report_2026-05-23.json`
- `docs/A-v2.4_provider_comparison_report_2026-05-23.json`

## 7. 多模态状态

讲法：

> 多模态不是笼统说支持，而是分组件验收：Vision LLM 已转绿，MinerU Linux sliced 已转绿，PaddleOCR 已正式列为 runtime compatibility boundary。

强调：

- Vision LLM：真实图片理解链路可用。
- MinerU Linux sliced：小页范围真实 PDF 解析可用。
- PaddleOCR：当前 WSL runtime 稳定失败在 PaddleX static runner，不进入默认 demo。

证据：

- `docs/A-v1.5_multimodal_acceptance_report_2026-05-20.json`
- `docs/A-v2.3_paddleocr_compatibility_report_2026-05-23.json`
- `docs/A-v2.3_bad_cases.md`

## 8. Evaluation / Bad Case / Trace

讲法：

> 项目不只看平均分，还把低分 case、可能根因和 trace 串起来，用来判断问题发生在召回、上下文、rerank 还是答案决策。

展示：

- evaluation 面板
- 低分 case
- trace 时间线
- 展开 trace 详情
- 查看原始 JSON

强调：

- bad case 是优化入口。
- trace 是定位依据。
- evaluation 是回归门槛。

## 9. 当前边界

讲法：

> 当前边界是刻意收口出来的，不把未转绿链路包装成已完成能力。

边界：

- 默认 demo 不依赖 PostgreSQL / Redis / Neo4j / Milvus。
- PaddleOCR 不进入默认 demo。
- MiMo 可作为候选 provider，对外默认仍使用 deepseek_chat。

## 10. 下一步

推荐说法：

> 技术主线已经具备演示闭环，下一步我会做公开交付检查，包括截图、敏感信息排查、公开仓库导出和最终作品集材料整理。
