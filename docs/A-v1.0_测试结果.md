# A-v1.0 公开版测试结果

## 范围

公开版只验证默认本地可复现链路，不把外部 Redis、PostgreSQL、Milvus、Neo4j 和真实视觉服务作为 CI 必须条件。

## 本轮结果

- 后端核心回归：
  - `backend/tests/test_api.py`
  - `backend/tests/test_enterprise_api.py`
  - `backend/tests/test_hybrid_retrieval.py`
  - `backend/tests/test_rag_security.py`
  - `backend/tests/test_release_scenarios.py`
  - `backend/tests/test_ticket_workflow.py`
- 代码质量：
  - `python -m ruff check backend`
  - `python -m compileall backend/app backend/scripts`
- 前端构建：
  - `npm run build`
- 工程配置：
  - `docker compose config`

## 验收重点

- 文档入库、问答、引用链路可用
- 混合检索与 rerank 主逻辑可用
- Prompt Injection 与危险操作防护可用
- 工单启动、HITL、恢复、关闭主链路可用
- Vue 前端可构建
- Docker Compose 配置可解析

## 发布判断

公开版测试口径已经从“全量研发验证”收敛到“对外发布必需能力验证”。后续如果增加公开仓库功能，继续优先补核心回归集，而不是把内部联调脚本直接纳入 CI。
