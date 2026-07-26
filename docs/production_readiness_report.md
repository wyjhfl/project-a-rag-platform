# Production Readiness Report

> 目标：明确 Project A 当前能证明什么、还不能证明什么，以及下一步如何从面试展示项目增强为 production-like 企业级 Agentic RAG 平台。

## 结论

Project A 当前适合作为强求职项目和 production-like showcase。

它已经具备：

- 企业设备售后诊断业务定位。
- Agentic RAG 诊断控制器。
- answer / refuse / escalate 决策边界。
- Trace 证据链和 GraphRAG 关系展示。
- Jobs、Tickets、Audit、Evaluation、Metrics、E2E、CI。
- SQLite demo 路径和 PostgreSQL / Redis / Grafana 生产增强路径。

它还不能直接宣称已经经过真实生产验证，因为仓库内没有真实线上流量、真实客户数据、长期运行报告和生产事故演练记录。

最准确的定位是：

> Production-like enterprise Agentic RAG platform with local demo, CI, E2E, smoke tests, worker stress, observability skeleton, and explicit production hardening roadmap.

## 当前生产就绪度分层

### 已具备的能力

- API 服务：FastAPI、Pydantic、OpenAPI schema。
- 前端控制台：Vue 3、TypeScript、Element Plus、Playwright E2E。
- RAG 能力：文档入库、hybrid retrieval、citations、拒答边界。
- Agentic 能力：安全检查、查询路由、动态检索、风险检查、工单升级。
- 状态管理：SQLite demo、PostgreSQL store、Jobs、Tickets、Audit、Trace。
- 可观测性：healthz、readyz、Request ID、Prometheus metrics、Grafana demo dashboard。
- 质量保障：pytest、ruff、OpenAPI drift、secret scan、Docker Compose config、Full E2E runner。
- 并发基础：Redis rate limit、PostgreSQL worker stress、worker concurrency tests。

### 当前不足

- 缺少真实生产流量验证。
- 缺少 HTTP API 高并发压测报告。
- 缺少 RAG / Agentic 诊断 P95、P99 延迟数据。
- 缺少长时间 soak test。
- 缺少线上资源占用曲线。
- 缺少生产告警规则和事故演练记录。
- 缺少真实企业文档和人工标注质量数据。

## 高并发 readiness 判断

当前项目不能直接宣称“支持高并发生产流量”。

可以诚实宣称：

- 已有 worker 并发和 PostgreSQL stress 证据。
- 已有 Redis 限流和 readyz degraded 设计。
- 已有 Prometheus metrics 暴露请求、错误、任务、Agent 决策等信号。
- 已补充 `scripts/load_test_http.py`，可对 healthz、readyz、chat、agentic、traces、graph、metrics 做 HTTP 压测。
- 下一步应在固定机器上执行 10/50/100 并发压测，产出 P50/P95/P99、错误率和瓶颈分析。

## 生产可用性风险

### LLM 外部依赖风险

RAG 和 Agentic 诊断可能依赖外部模型服务。

风险：

- 第三方模型延迟不稳定。
- API quota 或费用限制。
- 网络失败导致回答不可用。

缓解：

- 设置 timeout。
- 对高延迟或失败进行降级。
- 将 LLM latency、error、token usage 纳入 metrics。
- 对关键场景优先使用检索证据和拒答边界。

### 检索质量风险

风险：

- 文档不足导致召回失败。
- chunk 策略不合适导致引用不准确。
- query rewrite 改写不稳定。

缓解：

- 扩充 production-like eval cases。
- 输出 citation accuracy、refusal accuracy、escalation accuracy。
- 定期复盘 low-score trace。

### 状态一致性风险

风险：

- 多 worker 竞争任务。
- 工单或 Trace 写入失败。
- SQLite 不适合多实例生产。

缓解：

- 生产优先 PostgreSQL。
- 使用 worker stress 验证任务竞争。
- 加强 Alembic 迁移和备份恢复流程。

## 推荐生产化路线

### Phase 1：压测证据

- 执行 `scripts/load_test_http.py`。
- 覆盖 health、ready、chat、agentic、traces、graph、metrics。
- 记录 10/50/100 并发下的吞吐、P95、P99、错误率。
- 输出 `docs/load_test_report.md` 的实测版本。

### Phase 2：质量证据

- 扩充 `data/eval` 中的 production-like cases。
- 加强 unknown model、prompt injection、high risk、GraphRAG multi-hop 场景。
- 输出 `docs/rag_quality_report.md` 的实测版本。

### Phase 3：运维证据

- 使用 `docs/operation_runbook.md` 做故障演练。
- 补 Grafana 告警规则。
- 设计 OTel trace correlation。

### Phase 4：生产组件演进

- PostgreSQL 作为默认生产 store。
- Redis 用于限流、缓存和会话。
- 外部队列替换内置 JobService 的执行层。
- 完善 Alembic 回滚、备份和恢复。

## 面试表达

推荐说法：

> 这个项目我不会夸大成已经承载真实客户流量的生产系统。它是 production-like Agentic RAG 平台：已经有 CI、E2E、secret scan、OpenAPI drift、PostgreSQL smoke、Redis 限流、worker stress、Prometheus/Grafana 和生产验收门禁。当前短板是缺少真实线上流量和长期压测数据，所以我补了 HTTP load test 脚本、生产就绪度报告和运维 Runbook，用数据化方式继续逼近生产要求。
