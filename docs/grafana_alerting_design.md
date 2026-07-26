# Grafana Alerting Design

> 目标：把当前 Grafana demo dashboard 演进为生产级告警设计。

## 当前状态

项目已有：

- `/metrics` Prometheus 文本指标。
- Prometheus 配置。
- Grafana datasource。
- Grafana demo dashboard。
- Agent decision、RAG trace、retrieval retry、escalation 等指标基础。

当前缺口：

- 没有生产告警规则。
- 没有 SLO 目标。
- 没有告警分级。
- 没有 incident response 关联 Runbook。

## 建议 SLO

第一阶段不要设夸张目标，先设 demo / staging 目标：

- API availability：99% staging target。
- 5xx error rate：5 分钟窗口内小于 1%。
- healthz success：连续失败 3 次告警。
- readyz degraded：持续 5 分钟告警。
- Agentic RAG P95 latency：超过目标阈值时告警。
- retrieval retry rate：异常升高时告警。
- escalation count：异常突增时告警。
- job failed count：持续增长时告警。

## 告警分级

### P1

影响核心服务可用性。

例子：

- healthz 持续失败。
- API 5xx 大量增长。
- Store 连接失败。

处理：立即排查，优先恢复服务。

### P2

核心业务质量下降。

例子：

- Agentic RAG P95 延迟持续升高。
- refusal rate 异常升高。
- escalation rate 异常降低或异常升高。
- retrieval retry rate 异常升高。

处理：查看 Trace、Quality、Evaluation 和近期变更。

### P3

非核心但需要跟进。

例子：

- job failed count 增加。
- Grafana scrape 间歇失败。
- audit event 异常增长。

处理：排期修复或观察趋势。

## 推荐面板

- API request rate。
- API error rate。
- P50 / P95 / P99 latency。
- Agent decision count。
- RAG trace count。
- retrieval retry count。
- escalation count。
- job status count。
- readyz dependency status。
- Redis rate limit denied count。

## 告警到 Runbook 的关联

每条告警应附带 Runbook 入口：

- API 5xx：见 `docs/operation_runbook.md` 的 API 返回 500。
- RAG 质量下降：见 RAG 回答质量下降。
- Agentic 误拒答：见 Agentic RAG 误拒答。
- Jobs 失败：见 Jobs 卡住或失败。
- Redis 限流异常：见 Redis 限流异常。

## 实施路线

### Step 1：指标确认

确认 `/metrics` 中已有指标是否能覆盖告警需求。

### Step 2：补充缺失指标

优先补：

- latency histogram。
- readyz dependency labels。
- LLM provider error count。
- RAG insufficient count。
- citation empty count。

### Step 3：Grafana dashboard 增强

在现有 dashboard 中加入延迟、错误率和 Agentic 质量相关图表。

### Step 4：告警规则

为 P1/P2/P3 分别设计阈值，并在 staging 环境观察误报率。

## 面试表达

推荐说法：

> 当前项目已有 Prometheus/Grafana demo stack。下一步我会把它升级成告警体系：先定义 API availability、error rate、P95 latency、Agent decision、retrieval retry、escalation、job failed 等 SLO 信号，再把告警分成 P1/P2/P3，并关联 operation runbook。这样项目从能看指标，进一步走向能响应故障。
