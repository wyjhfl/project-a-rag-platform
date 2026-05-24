# A-v2.1 面试讲法索引

## 一句话介绍

Project A 是一个企业设备售后诊断 RAG 平台，把故障问答、引用证据、真实 LLM 验收、多模态验收、bad case、trace、evaluation 和工单闭环串成了可演示的工程系统。

## 这个项目和普通 RAG demo 的区别

普通 RAG demo 常见问题是：

- 只展示“能回答”
- 不证明答案是否 grounded
- 不记录失败 case
- 不区分 provider 失败原因
- 不知道多模态链路到底哪里可用
- 没有面向演示的状态入口

Project A 的区别：

- 回答必须绑定检索证据。
- 真实 LLM 需要通过 grounded 验收才进入默认候选。
- provider 失败会区分认证、配置、限流、服务端、grounded rejection。
- 多模态按 Vision、MinerU、PaddleOCR 分组件验收。
- evaluation、bad case、trace 形成排查闭环。
- 前端演示中心聚合真实报告，不靠口头说明。

## 如何控制幻觉

推荐回答：

> 我没有让真实 LLM 直接接管最终答案，而是在检索上下文之后做 grounded acceptance。只有当回答命中设备、故障码、上下文重合和具体排查动作时，才接受真实 LLM 输出。否则回退或明确资料不足。

可以补充：

- A-v1.4 修过一个关键问题：部分可答、部分资料不足的回答不应该一刀切拒绝。
- 当前 deepseek_chat 已通过 grounded 验收。
- 验收证据在 `A-v1.4_provider_acceptance_report_2026-05-19.json`。

## Provider 验收怎么设计

推荐回答：

> 我把 provider 验收拆成 auth preflight 和 grounded acceptance。先证明 key、base_url、model id 能连通，再证明它能在 RAG 上下文里生成可接受答案。

重点：

- `auth_invalid` 不等于模型能力差。
- `config_missing` 是配置问题。
- `grounded_rejection` 是回答没有通过项目约束。
- `accepted` 才能进入默认候选。

当前结论：

- `deepseek_chat` 是公开 demo 默认主链。
- MiMo token-plan 已在 A-v2.2 重新验收中转绿。
- A-v2.4 横向对比后，`mimo-v2.5` 作为候选 provider 对照，`mimo-v2.5-pro` 暂不进入默认演示路径。

## 多模态怎么验收

推荐回答：

> 我没有把多模态包装成一个笼统能力，而是拆成 Vision LLM、OCR、PDF parsing 和端到端 ingest。每个组件都输出状态、阻塞类型和下一步。

当前结论：

- Vision LLM：passed。
- MinerU Linux sliced：passed。
- PaddleOCR：runtime_incompatible。

专业解释：

> PaddleOCR 的阻塞不在业务代码入口，也不是单个图片样例问题，而是 paddle / paddleocr / paddlex runtime 组合在真实运行时失败，所以被定性为 runtime_incompatible。

## bad case 和 trace 怎么闭环

推荐回答：

> evaluation 不只看平均分。低分 case 会带 diagnostics 和 trace，可以看到它经过 security_check、query_route、retrieval、rerank、answer_decision 等节点，从而判断问题在召回、上下文噪声还是答案覆盖不足。

重点：

- bad case 是问题样本库。
- trace 是定位链路。
- evaluation 是回归基线。
- 前端演示中心把它们整合到一个页面里。

## 为什么要做前端验收中心

推荐回答：

> 因为项目进入后期后，能力和证据分散在很多 JSON 和 Markdown 里。前端验收中心把 provider、多模态、evaluation、bad case、trace 聚合成一个可讲的状态板，面试时不用翻文档，也能直接解释系统真实状态。

强调：

- 它不是宣传页。
- 它读取真实报告。
- 它能展示已转绿、阻塞、边界和证据文件。

## 当前项目最大亮点

推荐讲三点：

1. **真实验收意识**：不是“接了模型”就算完成，而是区分连通、grounded、默认候选。
2. **边界表达清楚**：MiMo 和 PaddleOCR 没有被包装成成功，而是明确阻塞层。
3. **工程闭环完整**：检索、回答、引用、评测、bad case、trace、演示中心形成链路。

## 当前短板怎么讲

MiMo：

> MiMo 已从旧认证阻塞推进到 token-plan 口径下的 grounded 可比较 provider。当前默认演示仍使用 DeepSeek，是因为现场延迟和稳定性更适合公开 demo；MiMo v2.5 适合作为 provider 对比亮点。

PaddleOCR：

> 当前已经做过 Windows 和 WSL/Linux 多轮真实探针，阻塞稳定收口在 Paddle/PaddleX runtime 兼容性。A-v2.3 已将它正式列为 runtime compatibility boundary，不进入默认 demo。

长文档 MinerU：

> MinerU Linux sliced 已可用，但整本长手册在 CPU profile 下仍有吞吐和超时边界，所以当前只承诺小页范围验收通过。

## 面试收束句

> 这个项目最重要的不是堆了多少 RAG 名词，而是每条能力都有验收状态、失败边界和证据链。它能说明我不仅会搭 RAG，还会把 RAG 做成可排查、可评测、可演示的工程系统。
