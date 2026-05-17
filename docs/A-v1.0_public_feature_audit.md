# A-v1.0 公开版功能核对表

## 结论

当前仓库已具备设计文档主链路中的核心功能。公开版保留最终实现、最小演示数据、核心测试与部署材料；对强依赖外部环境的能力采用“代码保留、文档弱化、默认关闭”的发布策略。

## 功能核对

| 功能项 | 代码入口 | 验收证据 | 公开版策略 |
|---|---|---|---|
| 文档入库与切片 | `backend/app/rag/documents.py` `backend/app/rag/chunker.py` | `backend/tests/test_api.py` | 保留 |
| 基础问答与引用 | `backend/app/rag/pipeline.py` | `backend/tests/test_api.py` | 保留 |
| SSE 流式输出 | `backend/app/main.py` | API 路由实现 | 保留 |
| BM25 / RRF / rerank | `backend/app/rag/keyword.py` `hybrid.py` `rrf.py` `reranker.py` | `backend/tests/test_hybrid_retrieval.py` | 保留 |
| 查询增强 / 路由 | `backend/app/rag/query_enhancement.py` | 已实现，公开版在 README 中弱化实验细节 | 代码保留、文档弱化 |
| 安全边界 | `backend/app/rag/security.py` | `backend/tests/test_rag_security.py` | 保留 |
| 多轮对话 | `backend/app/rag/conversation.py` | `backend/tests/test_release_scenarios.py` | 保留 |
| LangGraph 工单闭环 | `backend/app/ticketing/workflow.py` | `backend/tests/test_ticket_workflow.py` | 保留 |
| HITL / 工单恢复 / 关闭 | `backend/app/ticketing/` | `backend/tests/test_api.py` `test_ticket_workflow.py` | 保留 |
| 备件查询 | `backend/app/ticketing/parts.py` | `backend/tests/test_ticket_workflow.py` | 保留 |
| 评测入口 | `backend/app/main.py` `backend/scripts/run_regression.py` | `backend/tests/test_enterprise_api.py` | 保留 |
| Vue3 前端 | `frontend/src/` | `npm run build` | 保留 |
| Docker Compose | `docker-compose.yml` | `docker compose config` | 保留 |
| Redis 缓存 | `backend/app/cache/redis_cache.py` | `docs/A-v1.0_redis_真实缓存验收.md` | 代码保留、默认关闭 |
| PostgreSQL 存储 | `backend/app/storage/postgres_store.py` | `docs/A-v1.0_postgresql_真实存储验收.md` | 代码保留、默认关闭 |
| Milvus 向量库 | `backend/app/rag/vector_factory.py` | `docs/A-v1.0_milvus_multimodal_真实验收.md` | 代码保留、默认关闭 |
| Neo4j 图检索 | `backend/app/rag/graph.py` | `docs/A-v1.0_neo4j_真实联网验收.md` | 代码保留、默认关闭 |
| 真实多模态链路 | `backend/app/rag/multimodal.py` | `docs/A-v1.0_milvus_multimodal_真实验收.md` | 代码保留、默认关闭 |

## 不进入公开版的内容

- 本地运行产物：`data/chroma`、`data/v05_eval`、各类 `.db`、日志、PID
- 探针和联调残留：前端全量联调记录、预检 JSON、Neo4j probe 数据
- 大量研发过程文档：开发流水、调试日志、superpowers 计划稿、历史复盘
- 下载来的原始大文件资料：`data/raw_manuals_downloaded/` 下的 PDF 原件

## 发布判断

公开版已经满足“展示整体实现 + 支撑面试讲解 + 本地可跑 + CI 可验”的目标，不再继续携带研发噪音。
