# Resume / Interview Showcase - Project A

## 一句话定位

Project A 是一个企业设备售后诊断 Agentic RAG 平台，用单诊断控制器把设备型号、故障码和现场现象转成带引用、可追踪的排障建议，并在资料不足或高风险场景下拒答或升级人工工单。

## 30 秒开场白

我做的 Project A 不是普通聊天 demo，也不是多 Agent 平台，而是企业设备售后诊断 Agentic RAG 平台。它用单诊断控制器串起安全检查、query route、知识检索、risk check、工单升级，生成 grounded answer、引用证据和 trace_id；当资料不足或操作高风险时，会拒答或升级人工工单。工程上我做了异步 Job、审计日志、Request ID、Prometheus/Grafana、Alembic 迁移骨架、OpenAPI 类型同步、Playwright E2E、Docker Compose 和最终生产验收脚本，所以这个项目能展示 RAG 应用从 demo 到生产化落地的完整思路。

## 简历 bullet

### 中文版

企业设备售后诊断 Agentic RAG 平台：基于 LangGraph StateGraph 实现诊断 Agent（安全检查 → LLM 计划生成 → 路由 → 自适应检索 → LLM+规则双通道风险判级 → 拒答/升级人工工单，条件边表达决策分支），LLM 查询改写仅在低质量 retry 路径触发以控制 token 成本；接入 OpenAI 兼容 LLM 与 Embedding Provider（BGE/Qwen 等），未配置时降级为确定性离线实现保证 CI 可复现；配套 grounded 引用、Prompt 注入防护、Trace 持久化、GraphRAG 关系、异步 Job、审计日志、Prometheus/Grafana、Alembic、OpenAPI 类型同步、Playwright E2E 与 13 步生产验收门禁（FastAPI + Vue 3 + Chroma/Milvus + SQLite/PostgreSQL）。

### English version

Built an enterprise Agentic RAG diagnosis platform: a LangGraph StateGraph diagnosis agent (security check → LLM-generated plan → routing → adaptive retrieval → dual-channel LLM+rule risk assessment → refuse/escalate via conditional edges), with LLM query rewriting bounded to the low-quality retry path; pluggable OpenAI-compatible LLM and embedding providers (BGE/Qwen/OpenAI) that degrade to deterministic offline implementations for reproducible CI; plus grounded citations, prompt-injection guardrails, trace persistence, GraphRAG relations, async jobs, ticket escalation, audit logs, Prometheus/Grafana observability, Alembic migrations, OpenAPI-generated frontend types, Playwright E2E, and a 13-step production acceptance gate (FastAPI + Vue 3 + Chroma/Milvus + SQLite/PostgreSQL).

## 面试亮点

| 亮点 | 可以怎么讲 |
|---|---|
| LangGraph Agent | 诊断控制器是 StateGraph + 条件边，LLM 做计划与风险判级，关键词规则是安全下限（LLM 只能升险不能降险） |
| 优雅降级设计 | LLM/Embedding 未配置时自动退回确定性实现：同一套代码离线 CI 可复现，线上接真实模型 |
| RAG 不是聊天包装 | 检索、引用、拒答、评测、bad case 和工单闭环组成业务系统 |
| 异步 Job | 入库和评测不阻塞请求，支持 claim、cancel、retry、timeout、heartbeat |
| 可观测性 | Request ID、统一错误体、审计事件、Prometheus metrics 和 System Status UI |
| API 契约 | OpenAPI 导出生成前端类型，CI 检查 schema drift |
| 生产门禁 | final acceptance 一次性跑测试、构建、secret scan、Docker、PostgreSQL、Redis、E2E |
| 安全边界 | Prompt 注入防护、API Key 角色、上传限制、敏感 metadata 脱敏 |

## 面试官可能追问

### 为什么不是直接调用 LLM？

直接调用 LLM 无法保证答案基于企业资料，也缺少引用证据和拒答边界。这个项目把知识检索、引用证据、Prompt 注入防护、评测和人工升级做成闭环，目标是让答案可追溯、可验收、可运维。

### 怎么减少幻觉？

主要靠四层：检索上下文约束、grounded answer、引用证据、资料不足时拒答/升级人工。评测侧保留 regression/adversarial case 和 bad case 复盘，用指标和样本驱动改进。

### 异步任务为什么重要？

文档入库和评测可能耗时较长。同步接口会阻塞用户请求，不利于生产运维。JobService 把任务状态显式化，配合 worker claim、cancel、retry、timeout 和审计事件，可以在 UI 中解释任务生命周期。

### 如果多实例部署会怎样？

单实例 demo 可以用 SQLite + memory limiter。生产增强路径使用 PostgreSQL 存储 Job 状态、Redis 做限流共享，Docker Compose 提供 api/worker/web/postgres/redis/milvus。后续还可以把 JobService 演进到 Celery/RQ 等外部队列。

### 最大不足是什么？

Git 历史是 reconstructed，需要透明说明；真实模型（agnes-2.0-flash + bge-m3）已接入并完成一轮实测（regression 30/30、agentic 6/6、LLM-judge grounded 8/10），但评测集在 demo 语料上已饱和——哈希向量对照组分数相同，说明集合难度不足以区分检索后端，需要更大语料和改述式难例；faithfulness 判分目前是单票 LLM-as-judge 抽样，还没有人工标注对齐；OTel 链路追踪、生产级迁移治理、外部队列也在下一阶段计划里。这些不是回避项，而是已经写进质量报告的工程计划。

## GitHub 展示路径

1. 先看 README 顶部：定位、亮点、CI、快速启动。
2. 再看前端 Acceptance 页：面试展示卡片和验收数据。
3. 再看 `docs/architecture_overview.md`：确认架构分层。
4. 再看 `docs/interview_demo_script.md`：按 5-10 分钟 demo 走。
5. 最后看 `scripts/final_production_acceptance.ps1`：确认生产验收证据。
