# Load Test Report

> 目标：给 Project A 建立可复用的 HTTP 压测方法，避免在简历或面试中空泛声称“支持高并发”。

## 结论

当前仓库已经具备 worker 并发、PostgreSQL stress、Redis 限流和 metrics 基础，但此前缺少 HTTP API 层的系统化压测入口。

本轮新增：

- `scripts/load_test_http.py`

它使用 Python 标准库实现，不依赖 k6、Locust 或 aiohttp，适合本机 demo、CI smoke 和面试前快速验证。

## 压测脚本能力

支持场景：

- `health`：`GET /healthz`
- `ready`：`GET /readyz`
- `metrics`：`GET /metrics`
- `chat`：`POST /api/v1/chat`
- `agentic`：`POST /api/v1/agent/diagnose`
- `traces`：`GET /api/v1/rag/traces`
- `graph`：`GET /api/v1/rag/graph/relations`

输出指标：

- 请求总数。
- 并发数。
- 成功数和失败数。
- 错误率。
- 吞吐量 RPS。
- latency min / avg / p50 / p95 / p99 / max。
- status code 分布。
- error 类型分布。

## 推荐执行命令

基础健康检查：

```powershell
python scripts/load_test_http.py --scenario health --requests 100 --concurrency 10
```

readiness 检查：

```powershell
python scripts/load_test_http.py --scenario ready --requests 100 --concurrency 10
```

普通 RAG 问答压测：

```powershell
python scripts/load_test_http.py --scenario chat --requests 100 --concurrency 10 --json-out reports/load-chat-c10.json
```

Agentic RAG 诊断压测：

```powershell
python scripts/load_test_http.py --scenario agentic --requests 50 --concurrency 5 --json-out reports/load-agentic-c5.json
```

Trace 查询压测：

```powershell
python scripts/load_test_http.py --scenario traces --requests 100 --concurrency 10 --json-out reports/load-traces-c10.json
```

## 建议压测矩阵

第一轮建议按以下矩阵执行：

- 10 并发：验证基础稳定性。
- 50 并发：验证面试展示级压力。
- 100 并发：观察本机环境边界。
- 10 分钟持续压测：观察轻量 soak 行为。

推荐先测低成本接口：

1. `health`
2. `ready`
3. `metrics`
4. `traces`
5. `graph`

再测业务接口：

1. `chat`
2. `agentic`

原因：业务接口可能触发检索、模型调用、Trace 保存和工单逻辑，延迟和失败来源更复杂。

## 成功标准建议

本机 demo 环境不要夸大目标。建议第一阶段标准：

- health / ready：错误率为 0。
- traces / graph：10 并发下错误率小于 1%。
- chat：10 并发下错误率小于 5%，P95 不超过可接受 demo 阈值。
- agentic：5 并发下错误率小于 5%，P95 结合 LLM provider 延迟单独说明。

如果使用外部 LLM：

- 需要单独记录模型服务延迟。
- 不应把外部 provider 抖动误判为本项目 API 问题。
- 可以使用 mock 或本地 fallback 做纯后端链路压测。

## 当前尚未包含的证据

本报告当前不写虚构压测数字。

尚需在目标机器上实际执行并补充：

- CPU / memory 使用情况。
- RPS 曲线。
- P95 / P99 曲线。
- 错误请求样本。
- PostgreSQL 连接和锁等待情况。
- Redis 限流命中情况。
- Grafana 截图或导出 JSON。


## 2026-07-04 本机轻量压测结果

执行环境：

- 日期：2026-07-04。
- 机器：本机 Windows 开发环境。
- 后端启动方式：`uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`。
- 环境变量：`AUTH_ENABLED=false`、`METRICS_ENABLED=true`、`VECTOR_BACKEND=chroma`、`STORAGE_BACKEND=sqlite`、`APP_ENV=load-test`。
- 压测工具：`scripts/load_test_http.py`。
- 结果文件：`docs/load_test_results_2026-07-04.json`。

边界说明：

- 这是本机 production-like smoke load test，不是线上生产压测。
- Chat 和 Agentic 场景采用低并发，目标是验证链路、延迟和错误率，不宣称高并发容量上限。
- 当前结果受本机 CPU、磁盘、Python 运行时、SQLite、Chroma、本地数据规模和 LLM/fallback 路径影响。
- 后续如要对外宣称容量，需要在固定机器、固定数据集、固定模型 provider 下重复执行并保留资源监控截图。

| 场景 | 请求数 | 并发 | RPS | avg ms | p50 ms | p95 ms | p99 ms | 错误率 | 状态码 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| health | 100 | 10 | 146.826 | 66.118 | 50.19 | 231.278 | 238.233 | 0.0 | {'200': 100} |
| ready | 100 | 10 | 157.374 | 60.834 | 43.53 | 234.856 | 239.255 | 0.0 | {'200': 100} |
| metrics | 50 | 5 | 133.302 | 35.943 | 26.838 | 105.782 | 110.109 | 0.0 | {'200': 50} |
| traces | 50 | 5 | 187.452 | 25.391 | 15.44 | 100.662 | 102.203 | 0.0 | {'200': 50} |
| graph | 50 | 5 | 161.483 | 29.115 | 14.889 | 76.115 | 84.218 | 0.0 | {'200': 50} |
| chat | 20 | 2 | 29.992 | 65.836 | 46.508 | 152.309 | 184.515 | 0.0 | {'200': 20} |
| agentic | 10 | 2 | 22.334 | 86.349 | 77.282 | 149.895 | 149.895 | 0.0 | {'200': 10} |

初步判断：

- health、ready、metrics、traces、graph 均在本机轻量并发下 0 错误。
- chat 和 agentic 低并发链路均 0 错误，可作为后续扩大压测的基线。
- 本轮还不能证明真实生产高并发能力，但已经把“能否压测”升级为“有脚本、有结果、有边界说明”。

下一轮建议：

1. 在同一机器上执行 50/100 并发的 health、ready、metrics、traces、graph。
2. 对 chat 和 agentic 逐步提升到 5/10/20 并发，并记录是否触发外部 LLM 限制。
3. 同时采集 CPU、内存、磁盘和 `/metrics` 指标。
4. 将 Grafana 截图或 dashboard export 追加到本报告，并同步更新 `docs/load_test_results_2026-07-04.json`。

## 高并发面试表达

推荐说法：

> 当前项目已经有 worker concurrency、PostgreSQL worker stress、Redis rate limit 和 Prometheus metrics，但我不会直接宣称经历过真实生产高并发。为补齐 HTTP 层证据，我新增了标准库压测脚本，覆盖 health、ready、chat、agentic diagnose、Trace 和 GraphRAG 接口，输出 RPS、错误率、P50/P95/P99 和状态码分布。下一步会在固定环境执行 10/50/100 并发矩阵，形成可复现的 load test report。
