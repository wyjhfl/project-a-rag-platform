# Interview Questions - Project A

这份文档用于面试前快速复盘。回答重点不是背概念，而是把每个问题都落到 Project A 的具体设计、代码和验收证据上。

## 1. 你这个项目和普通 ChatGPT 套壳有什么区别？

普通聊天套壳只负责把用户输入转发给 LLM。Project A 的目标是企业设备售后诊断，所以核心是“可引用、可拒答、可评测、可追踪、可升级人工”：

- 文档入库和检索提供企业知识上下文。
- 回答需要 grounded answer 和引用证据。
- 资料不足或高风险操作时拒答或升级工单。
- Evaluation、bad case、trace 用来复盘质量。
- Audit、Request ID、metrics 用来排障和运维。

## 2. RAG 幻觉怎么控制？

我把幻觉控制拆成四层：

1. **检索层**：尽量召回相关资料，并通过上下文约束回答范围。
2. **生成层**：要求回答绑定引用证据，不把模型常识当企业资料。
3. **边界层**：资料不足、高风险维修、对抗输入时拒答或升级人工。
4. **评测层**：用 regression、adversarial、RAGAS 风格指标和 bad case 复盘持续改进。

面试演示时可以打开 Acceptance 页的 “RAG 质量证据” 卡片，讲 `context_precision`、`faithfulness` 和 `context_recall`。

## 3. 为什么要做异步 Job？

文档入库和评测可能耗时较长，如果同步执行会阻塞请求，也不利于失败重试和运维排障。Project A 把这类操作抽象为 Job：

```text
PENDING -> RUNNING -> SUCCEEDED / FAILED / CANCELLED
```

关键点：

- worker claim 避免多个 worker 重复执行同一个任务。
- cancel/retry/timeout/heartbeat 让任务生命周期更接近生产系统。
- Job 结果、错误摘要、审计事件和 metrics 都能在前端展示。

## 4. 如果部署多个 API/Worker 实例会有什么问题？

单实例 demo 路径可以使用 SQLite 和内存限流；多实例生产场景需要共享状态：

- Job 状态使用 PostgreSQL，避免不同 worker 看不到彼此状态。
- Rate limit 使用 Redis，避免每个实例各限各的。
- 当前内置 JobService 展示了任务语义，后续可以演进为 Celery/RQ/Redis Queue。

这也是我在文档中明确列出的技术取舍：先保证面试 demo 可运行，再保留生产增强路径。

## 5. 为什么要用 OpenAPI 生成前端类型？

前后端手写类型很容易 drift。Project A 通过 `scripts/export_openapi.py` 导出 `docs/openapi.json`，再用 `openapi-typescript` 生成 `frontend/src/api/generated.ts`。CI 和最终验收脚本都会检查 OpenAPI drift。

这样面试时可以讲：

- 后端 schema 是 API 契约源头。
- 前端类型从契约生成。
- CI 阻断“后端改了、前端不知道”的问题。

## 6. 怎么做可观测性？

Project A 有四类信号：

- `/healthz`：进程是否活着。
- `/readyz`：依赖是否就绪，可返回 degraded。
- `/metrics`：Prometheus 文本指标，前端 System Status 会解析 summary。
- Audit events：记录关键业务事件，例如 job.create、job.succeeded、job.failed、job.cancelled。

此外，统一错误体包含 `request_id`，前端错误卡片支持复制 Request ID，方便从 UI 追到日志和审计。

## 7. 安全方面做了什么？

主要包括：

- X-API-Key 角色权限：viewer < operator < admin。
- PromptInjectionGuard：拦截常见 prompt injection 输入。
- 上传安全：限制类型和大小。
- 审计 metadata 脱敏：敏感 key 屏蔽，复杂对象截断。
- Secret scan：最终验收脚本检查真实密钥泄露。

## 8. 这个项目最大的不足是什么？

我会主动说三个不足：

1. Git 历史是 reconstructed，需要透明说明，但代码、验收和发布证据是当前可信基础。
2. `/metrics` 已经有 Prometheus 文本端点，但还没有 Grafana/OTel 面板。
3. 内置 JobService 已覆盖任务语义，但多实例大规模生产更适合外部队列。

这三个不足都不是“没考虑”，而是已记录在后续路线图里。

## 9. 如果让你继续优化，你会先做什么？

优先级：

1. Grafana / OTel，把 metrics 从文本端点升级为可视化面板。
2. Alembic 管理生产数据库迁移。
3. 外部队列替代内置 JobService，提升多实例调度能力。
4. 扩容真实业务样本和 bad case，持续改进 RAG 指标。
5. 增加更多端到端真实 LLM 验收样本。

## 10. 面试收束话术

“这个项目我最想展示的是：我不是只会调 LLM API，而是知道一个 RAG 应用从业务场景、检索、引用、拒答、评测、异步任务、审计、metrics、CI 到生产验收需要哪些工程环节。项目仍然有后续优化空间，但当前已经能完整展示 AI 应用工程化落地能力。”
