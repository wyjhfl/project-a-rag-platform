# A-v1.3 真实多模态与企业增强验收

## 1. 本轮目标

A-v1.3 不新增 RAG 业务能力，重点把 Project A 的增强链路从“各自验收过”收成“统一可解释验收体系”。

本轮统一回答四个问题：

- 默认 `.env` 下真实 LLM 当前到底稳不稳定。
- 候选 provider 是否已经能接管 grounded 主链。
- Redis / PostgreSQL / Milvus / Neo4j 这些企业增强能力当前是什么状态。
- MinerU / PaddleOCR / Vision LLM 这些真实多模态链路当前卡在哪一层。

## 2. 为什么这一版必须做

到 A-v1.2 结束时，项目已经有很多“局部真证据”：

- Redis 真实缓存验收
- PostgreSQL 真实存储验收
- Neo4j 真实联网验收
- Milvus 与多模态真实验收
- 真实 LLM grounded 预检

但这些材料还是分散的。  
如果没有 A-v1.3，就很难快速说明：

```text
默认主链能不能稳定演示
候选模型到了哪一步
哪些增强能力已通过
哪些能力只是代码接通但被环境或凭证阻塞
```

## 3. 本轮做了什么

### 3.1 Provider 稳定性验收脚本

新增：

- `backend/scripts/run_provider_acceptance.py`
- `docs/A-v1.3_provider_manifest.example.json`

它会对同一批 provider 逐个调用：

```text
preflight_real_llm_grounding.py
-> direct_llm_connected
-> chat_grounded_llm
-> critical_failures
-> provider status
```

provider status 分三档：

- `accepted`：直连通过，grounded 主链也通过
- `unstable`：直连通过，但 grounded 主链不稳定
- `blocked`：直连就没有通过

### 3.2 企业增强统一验收脚本

新增：

- `backend/scripts/run_av13_acceptance.py`

它会把这些现有证据统一汇总：

- `docs/A-v1.0_postgresql_真实存储验收.md`
- `docs/A-v1.0_redis_真实缓存验收.md`
- `docs/A-v1.0_neo4j_真实联网验收.md`
- `docs/A-v1.0_milvus_multimodal_真实验收.md`
- `docs/A-v1.3_provider_acceptance_report.json`

最终生成：

- `docs/A-v1.3_acceptance_report.json`

### 3.3 预检稳定性补强

补充修正：

- `backend/app/rag/vector_store.py`
  - `ChromaVectorStore.reset()` 改为幂等，collection 不存在时不再误抛异常
- `backend/app/main.py`
  - 对外版本号更新为 `v1.3`

## 4. 当前真实结果

### 4.1 Provider 验收结果

来自：

- `docs/A-v1.3_provider_acceptance_report.json`

当前结果：

```text
default_env (mimo-v2.5-pro): blocked
deepseek-chat: unstable
```

这代表：

- 默认 `.env` 下的小米模型当前没有通过最小 grounded 验收。
- DeepSeek 已经能直连，但自动化 grounded 主链仍不稳定，不能作为默认配置直接切换。

### 4.2 企业增强验收结果

来自：

- `docs/A-v1.3_acceptance_report.json`

当前总览：

```text
passed: 4
unstable: 1
blocked: 4
```

具体分布：

- `passed`
  - PostgreSQL structured store
  - Redis cache
  - Neo4j graph retrieval
  - Milvus vector store
- `unstable`
  - DeepSeek candidate provider
- `blocked`
  - Default MiMo provider
  - MinerU real PDF parsing
  - PaddleOCR real runtime
  - Vision LLM real runtime

## 5. 这版的工程价值

A-v1.3 的价值不是“把所有增强能力都做成默认开启”，而是把边界说实：

```text
哪些能力默认可跑
哪些能力已通过真实验收
哪些能力是候选但不稳定
哪些能力被环境 / 凭证阻塞
```

这会直接提升：

- 发布可信度
- 面试抗追问能力
- 后续版本选择方向的清晰度

## 6. 当前边界

这版没有做下面这些更重的事：

- 没有把 DeepSeek 或其它 provider 改成默认 `.env`
- 没有修通 MinerU / PaddleOCR / Vision LLM 的外部环境阻塞
- 没有做前端验收看板页面

因为 A-v1.3 的最小目标是先把“验收口径”做实，而不是先把所有外部能力都强行打通。
