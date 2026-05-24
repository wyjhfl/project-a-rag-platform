# A-v1.0 公开版功能核对表（A-v1.1 收敛版）

## 结论

当前仓库已经具备设计文档主链路中的核心功能。  
A-v1.1 的工作不是扩功能，而是把“功能项 -> 代码入口 -> 证据材料 -> 公开策略”重新收紧，避免 README、面试讲法和真实仓库状态继续漂移。

## 默认主链能力

| 功能项 | 代码入口 | 默认主链证据 | 公开版策略 |
|---|---|---|---|
| 文档入库与切片 | `backend/app/rag/documents.py` `backend/app/rag/chunker.py` | `backend/tests/test_api.py` | 保留 |
| 基础问答与引用 | `backend/app/rag/pipeline.py` | `backend/tests/test_api.py` | 保留 |
| SSE 流式输出 | `backend/app/main.py` | `/api/v1/chat/stream` 路由实现 | 保留 |
| BM25 / RRF / rerank | `backend/app/rag/keyword.py` `backend/app/rag/hybrid.py` `backend/app/rag/rrf.py` `backend/app/rag/reranker.py` | `backend/tests/test_hybrid_retrieval.py` | 保留 |
| 查询增强 / 路由 | `backend/app/rag/query_enhancement.py` | `backend/tests/test_query_enhancement.py` | 保留 |
| 安全边界 | `backend/app/rag/security.py` | `backend/tests/test_rag_security.py` | 保留 |
| 多轮会话 | `backend/app/rag/conversation.py` | `backend/tests/test_release_scenarios.py` `backend/tests/test_conversation.py` | 保留 |
| LangGraph 工单闭环 | `backend/app/ticketing/workflow.py` | `backend/tests/test_ticket_workflow.py` | 保留 |
| HITL / 工单恢复 / 关闭 | `backend/app/ticketing/` | `backend/tests/test_api.py` `backend/tests/test_ticket_workflow.py` | 保留 |
| 备件查询 | `backend/app/ticketing/parts.py` | `backend/tests/test_ticket_workflow.py` | 保留 |
| 评测入口 | `backend/app/main.py` `backend/scripts/run_regression.py` | `backend/tests/test_enterprise_api.py` | 保留 |
| Vue3 前端 | `frontend/src/` | `npm run build` | 保留 |
| Docker Compose | `docker-compose.yml` | `docker compose config` | 保留 |

## 可选增强能力

| 功能项 | 代码入口 | 可选增强证据 | 公开版策略 |
|---|---|---|---|
| Redis 缓存 | `backend/app/cache/redis_cache.py` | `docs/A-v1.0_redis_真实缓存验收.md` | 代码保留、默认关闭 |
| PostgreSQL 存储 | `backend/app/storage/postgres_store.py` | `docs/A-v1.0_postgresql_真实存储验收.md` | 代码保留、默认关闭 |
| Milvus 向量库 | `backend/app/rag/vector_factory.py` `backend/app/rag/vector_store.py` | `docs/A-v1.0_milvus_multimodal_真实验收.md` | 代码保留、默认关闭 |
| Neo4j 图检索 | `backend/app/rag/graph.py` | `docs/A-v1.0_neo4j_真实联网验收.md` | 代码保留、默认关闭 |
| 真实多模态链路 | `backend/app/rag/multimodal.py` | `docs/A-v1.0_milvus_multimodal_真实验收.md` | 代码保留、默认关闭 |

## A-v1.1 收口后的判断

- 默认主链证据已经能覆盖 README 中对外承诺的核心能力。
- 可选增强能力都能找到代码入口和至少一份真实验收或调试材料。
- 公开版仍然坚持“默认主链可跑，增强能力按需开启”，不把外部依赖变成默认承诺。

## 不进入公开版默认前提的内容

- 本地运行产物：`data/chroma`、`data/v05_eval`、各类 `.db`、日志、PID。
- 下载来的原始 PDF / 大文件资料。
- 针对单机环境的联调残留、探针数据和本地临时记录。
- 需要额外凭证或外部服务才能稳定运行的增强链路。

## 当前发布判断

当前仓库已经满足：

- 展示整体实现。
- 支撑面试讲解。
- 本地跑通主链。
- 用集中证据材料回答“默认能跑什么、增强项是什么、证据在哪里”。

A-v1.1 之后，这份核对表主要承担“公开宣称能力基线”职责，不再兼做研发过程记录。
