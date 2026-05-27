# A-v5.1 生产部署健康检查与优雅关闭报告

## 目标

补齐生产部署最基础能力：liveness 探针、readiness 探针、graceful shutdown、docker-compose healthcheck。

## /healthz

只检查进程存活，不检查任何依赖。用于 Kubernetes liveness probe 或负载均衡器健康检查。

```json
{"status": "ok", "service": "project-a-rag-platform", "version": "v2.0"}
```

## /readyz 状态规则

检查四项依赖：config、storage、vector_store、optional_dependencies。

| 条件 | HTTP 状态码 | body.status |
|------|-------------|-------------|
| config/storage/vector_store 全部 ok（vector_store 允许 degraded），可选依赖无异常 | 200 | ok |
| config/storage/vector_store 有 error | 503 | error |
| 核心检查无 error，但可选依赖有 error: 或 degraded: 前缀 | 200 | degraded |

## storage 检查

通过 `store.list_chat_records()` 验证存储后端可用。返回结构包含 `backend` 字段标识当前后端类型（sqlite / postgres）。

```json
{"status": "ok", "backend": "sqlite"}
```

## optional dependencies 降级规则

可选依赖（Redis、Milvus、Neo4j）按配置检查：

- 未启用：返回 `"disabled"`，不影响整体状态
- 启用但异常：返回 `"error: <原因>"` 或 `"degraded: <原因>"`
- 核心检查全部 ok 时，可选依赖有 error:/degraded: 前缀 → 整体 status 降为 degraded，HTTP 仍为 200

## docker-compose healthcheck

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/readyz')"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

## graceful shutdown

使用 FastAPI lifespan 上下文管理器：

- startup：记录日志
- shutdown：关闭 Redis 连接（如果启用），Chroma/SQLite 依赖 Python GC

## 验证结果

| 检查项 | 结果 |
|--------|------|
| ruff check main.py | All checks passed! |
| ruff check test_health_readiness.py | All checks passed! |
| pytest test_health_readiness.py | 10 passed |
| docker-compose.yml YAML 语法 | OK |

## 风险边界

- /readyz 不暴露密钥、绝对路径、用户名
- 可选依赖 error 不触发 503，只降级为 degraded
- vector_store 为 degraded 时仍返回 200，因为服务可降级运行
- graceful shutdown 只关闭 Redis 连接，Chroma/SQLite 依赖 GC
