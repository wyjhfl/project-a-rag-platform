# A-v2.7 面试材料压缩包

## 使用方式

这份材料用于面试前最后压缩，不替代完整证据文档。

推荐顺序：

```text
先背 2 分钟版
-> 熟悉 5 分钟演示版
-> 准备 15 分钟深挖版
-> 用高频追问补防守
```

## 2 分钟版

我做的 Project A 是一个企业设备售后诊断 RAG 平台，不是普通聊天 demo。

它从设备故障描述出发，完成知识检索、引用证据、grounded 回答、evaluation、bad case、trace，以及工单和人工升级闭环。

我重点做了三件事：

- 第一，文本主链不是“接上 LLM 就算完成”，而是做 provider auth preflight 和 grounded acceptance。当前 `deepseek_chat` 是公开 demo 默认主链，MiMo token-plan 已经在 A-v2.2 重新验收转绿，并在 A-v2.4 做了横向对比。
- 第二，多模态没有笼统说支持，而是拆开验收。Vision LLM 和 MinerU Linux sliced 已转绿，PaddleOCR 已明确为 runtime compatibility boundary，不进入默认演示路径。
- 第三，我做了前端验收中心，把 provider、多模态、evaluation、bad case、trace 和原始 JSON 聚合起来，面试时能直接展示真实证据链。

这个项目最能体现的是：我不只是会搭 RAG，而是能把 RAG 做成可验收、可排查、可演示、边界清楚的工程系统。

## 5 分钟演示版

### 0:00 - 0:40 项目定位

一句话：

> Project A 是一个企业设备售后诊断 RAG 平台，把故障描述、知识检索、引用回答、评测、trace 和工单闭环串成一个可演示系统。

强调：

- 面向设备售后诊断。
- 不是普通聊天问答。
- 核心是可验证业务闭环。

### 0:40 - 1:20 Demo 画像

讲法：

> 公开演示固定为 `sqlite + chroma + deepseek-chat`，这样现场最稳。企业增强能力如 Redis、PostgreSQL、Milvus、Neo4j 有代码入口和部分验收记录，但不放进默认 demo 前提。

展示：

- `.env.demo.example`
- `scripts/start_demo_stack.ps1`
- `docs/demo_guide.md`

### 1:20 - 2:20 验收中心

讲法：

> 前端验收中心不是静态宣传页，而是读取仓库里的真实 JSON 和 Markdown 报告，聚合 provider、多模态、evaluation、bad case 和 trace 状态。

展示：

- Provider 状态。
- 多模态状态。
- evaluation 和 bad case。
- trace 时间线和原始 JSON。

### 2:20 - 3:20 Provider 主线

讲法：

> 我把 provider 验收拆成两层：先确认 key、base_url、model id 能连通，再确认它能在 RAG 上下文里生成 grounded 答案。

当前结论：

- `deepseek_chat`：默认公开 demo 主链。
- `mimo-v2.5`：候选 provider，对比亮点。
- `mimo-v2.5-pro`：不进默认演示路径，因为 A-v2.4 中延迟和 fallback 表现不如默认主链。

证据：

- `docs/A-v2.2_provider_acceptance_report_2026-05-23.json`
- `docs/A-v2.4_provider_comparison_report_2026-05-23.json`

### 3:20 - 4:10 多模态边界

讲法：

> 多模态按组件验收，不把未转绿链路包装成成功。

当前结论：

- Vision LLM 已转绿。
- MinerU Linux sliced 已转绿。
- PaddleOCR 是 runtime compatibility boundary。

证据：

- `docs/A-v1.5_multimodal_acceptance_report_2026-05-20.json`
- `docs/A-v2.3_paddleocr_compatibility_report_2026-05-23.json`

### 4:10 - 5:00 收束

讲法：

> 这个项目最重要的不是堆 RAG 名词，而是每条能力都有真实验收、证据文件和失败边界。bad case 和 trace 能说明问题发生在召回、上下文、rerank 还是答案决策。

收束句：

> 所以它展示的是一个能落地、能排查、能演示的 RAG 工程系统。

## 15 分钟深挖版

### 1. 业务问题

设备售后诊断里，用户经常只给出设备型号、故障码或现场现象。

如果只是普通 LLM 回答，风险是：

- 幻觉排障步骤。
- 没有引用依据。
- 无法追踪失败原因。
- 无法把复杂问题升级到人工和工单。

Project A 的切入点是把诊断过程工程化：

```text
故障描述
-> 查询增强 / 检索
-> rerank
-> grounded answer
-> 引用证据
-> evaluation / bad case / trace
-> 工单闭环
```

### 2. RAG 主链

主链重点不是“能回答”，而是：

- 文档解析和切片。
- 向量检索与混合检索。
- rerank。
- 引用返回。
- SSE / API / 前端展示。
- grounded acceptance。

面试可讲：

> 我把真实 LLM 输出放在检索上下文之后校验，只有命中设备、故障码、上下文重合和具体排查动作时才接管最终答案，否则回退或明确资料不足。

### 3. Provider 验收

拆成两层：

- auth preflight：验证 key、base_url、model id 和基础连通。
- grounded acceptance：验证真实 RAG case 下能否生成可接受答案。

这样能区分：

- `auth_invalid`：认证问题。
- `config_missing`：配置问题。
- `grounded_rejection`：回答没过项目约束。
- `accepted`：可进入候选链路。

当前结论：

- DeepSeek 适合默认公开演示。
- MiMo v2.5 适合做 provider 对比亮点。
- MiMo v2.5 Pro 暂不作为默认主链。

### 4. 多模态验收

多模态拆成：

- Vision LLM。
- PDF parsing / MinerU。
- OCR / PaddleOCR。
- 端到端 ingest。

当前只承诺已转绿部分：

- Vision LLM。
- MinerU Linux sliced。

PaddleOCR 的问题被定性为 runtime compatibility boundary，因为多轮真实探针稳定失败在 Paddle / PaddleOCR / PaddleX runtime 组合，不是业务代码或单个样本问题。

### 5. Evaluation / Bad Case / Trace

讲法：

> 我不只看平均分，而是把低分 case、diagnostics 和 trace 串起来，定位问题发生在哪个环节。

可讲链路：

- evaluation 发现低分。
- bad case 记录失败样本。
- trace 展开关键节点。
- 判断是召回、上下文噪声、rerank 还是答案决策。
- 修复后再回归。

### 6. 前端验收中心

前端价值：

- 不用翻散落文档。
- 能直接展示真实验收状态。
- 能把“已转绿 / 阻塞 / 边界 / 证据文件”讲清楚。

面试可讲：

> 这个页面不是营销页，而是工程验收中心。它读取真实报告，把项目当前状态聚合成可演示状态板。

### 7. 当前边界

必须主动讲：

- 默认 demo 不依赖企业增强组件。
- PaddleOCR 不进入默认 demo。
- MiMo 是候选 provider，不替代默认主链。
- 长文档 MinerU 仍有吞吐和超时边界。

边界讲清楚，反而说明项目可信。

## 高频追问

### Q1：你怎么避免 RAG 幻觉？

答：

> 我不是让 LLM 直接回答，而是先检索上下文，再做 grounded acceptance。答案需要命中设备、故障码、上下文重合和具体排查动作。上下文不足时不强答，而是回退或明确资料不足。

### Q2：为什么默认用 DeepSeek，不用 MiMo？

答：

> MiMo token-plan 已经转绿，不是能力失败。但 A-v2.4 横向对比里，DeepSeek 的现场延迟和稳定性更适合公开 demo。MiMo v2.5 更适合作为候选 provider 和对比亮点。

### Q3：PaddleOCR 没转绿是不是多模态失败？

答：

> 不是。多模态被拆成 Vision、MinerU、PaddleOCR 等组件。Vision LLM 和 MinerU Linux sliced 已转绿，PaddleOCR 被单独定性为 runtime compatibility boundary。这个边界来自真实探针，不是口头推测。

### Q4：这个项目和普通 RAG demo 最大区别是什么？

答：

> 普通 demo 往往只证明能回答。这个项目证明的是每条能力能否验收、失败在哪里、证据是什么、怎么回归。核心是工程闭环和可观测性。

### Q5：bad case 怎么用？

答：

> bad case 是优化入口。低分 case 会关联 diagnostics 和 trace，我可以看到它经过 retrieval、rerank、answer decision 等节点，从而判断是召回不足、上下文噪声还是答案覆盖不足。

### Q6：如果要继续优化，你先做什么？

答：

> 我会先做面试和作品集侧的压缩表达，因为主链已经可演示。技术上优先补作品集截图，其次再考虑单独开 Docker clean runtime matrix 处理 PaddleOCR。

### Q7：你在项目里最能体现工程能力的点是什么？

答：

> 我没有把接入成功等同于能力成功，而是把 provider、多模态、evaluation、bad case 和 trace 都做成可验收证据。这个习惯更接近真实工程交付。

## 反问收束

可以问面试官：

> 贵团队现在 RAG 系统更关注召回质量、答案可信度、评测回归，还是线上可观测性？我这个项目里这几块都有做，可以按您关注的方向展开。

## 一句话备用收束

> Project A 的重点不是“用了哪些 RAG 技术”，而是把设备售后诊断做成了可验证、可追踪、可演示、边界清楚的 RAG 工程系统。
