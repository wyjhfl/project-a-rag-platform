# Project A: 企业设备售后诊断与工单闭环 RAG 平台

Project A 是一个面向企业设备售后场景的 RAG 工程项目，目标不是只做问答，而是把“故障描述 -> 检索诊断 -> 引用证据 -> 工单推进”串成一条可演示、可验证、可部署的业务闭环。

当前公开版聚焦最终可运行实现，保留核心工程能力与最小验证材料，不包含大量研发过程记录、临时探针和本地运行产物。

## 核心能力

- 基础 RAG：文档入库、切片、向量检索、问答、引用、SSE 流式响应
- 检索增强：BM25、RRF、rerank、查询增强、查询路由
- 安全边界：Prompt Injection 拦截、资料不足拒答、危险操作安全提示
- 多轮对话：会话级设备型号和故障码指代消解
- 工单闭环：LangGraph 工单流、HITL、人审恢复、备件查询、工单关闭
- 工程化：FastAPI 后端、Vue3 前端、Docker Compose、核心自动化测试、GitHub Actions CI
- 可选外部增强：Redis、PostgreSQL、Milvus、Neo4j、真实多模态解析与视觉 LLM

## 技术栈

- 后端：FastAPI
- 前端：Vue3 + Vite + TypeScript + Element Plus
- RAG 编排：LangChain / LangGraph
- 默认向量存储：Chroma
- 默认结构化存储：SQLite
- 可选增强：PostgreSQL、Redis、Milvus、Neo4j、MinerU、PaddleOCR

## 仓库结构

```text
backend/app/         FastAPI、RAG、工单与存储实现
backend/tests/       公开版核心回归测试
backend/scripts/     保留的评测与发布辅助脚本
frontend/            Vue3 演示前端
data/seed_docs/      最小演示文档
data/real_manuals_sanitized/  脱敏后的真实资料样例
data/eval/           回归与发布场景用例
docs/                公开版说明、功能核对、测试结果与 bad cases
prompts/             RAG prompt 文件
```

## 快速启动

### 1. 安装后端依赖

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`。

默认情况下，不配置真实 LLM 也可以本地跑通主链路，系统会回退到抽取式答案生成。

### 3. 启动后端

```powershell
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 18081 --reload
```

### 4. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

访问地址：

- 前端：[http://127.0.0.1:5173](http://127.0.0.1:5173)
- 后端健康检查：[http://127.0.0.1:18081/health](http://127.0.0.1:18081/health)

## Docker Compose

```powershell
docker compose up --build
```

访问地址：

- Web：[http://127.0.0.1:18080](http://127.0.0.1:18080)
- API：[http://127.0.0.1:18081](http://127.0.0.1:18081)

## API 摘要

```text
GET  /health
GET  /api/v1/system/status
POST /api/v1/documents/ingest
POST /api/v1/documents/upload
POST /api/v1/chat
POST /api/v1/chat/session
POST /api/v1/chat/stream
POST /api/v1/tickets/start
GET  /api/v1/tickets
POST /api/v1/tickets/{ticket_id}/resume
POST /api/v1/tickets/{ticket_id}/close
POST /api/v1/evaluations/run
```

## 默认可跑与可选增强

默认本地可跑：

- SQLite
- Chroma
- 脱敏演示资料
- 核心 API / 检索 / 工单 / 安全 / 评测入口

可选增强能力，通过 `.env` 打开：

- `CACHE_ENABLED=true`：Redis 缓存
- `STORAGE_BACKEND=postgres`：PostgreSQL 结构化存储
- `VECTOR_BACKEND=milvus`：Milvus 向量库
- `GRAPH_RETRIEVAL_ENABLED=true`：Neo4j 图检索
- `MULTIMODAL_BACKEND=real`：真实 MinerU / PaddleOCR / Vision LLM 链路

这些增强能力不是公开仓库 CI 的默认前提。

## CI

仓库提供 GitHub Actions，默认校验：

- `ruff check backend`
- 核心 `pytest`
- `python -m compileall backend/app backend/scripts`
- `npm ci`
- `npm run build`
- `docker compose config`

CI 只验证本地可复现链路，不依赖外部 Redis / PostgreSQL / Milvus / Neo4j / 真实视觉服务。

## 核心验证命令

```powershell
pytest backend/tests/test_api.py `
  backend/tests/test_enterprise_api.py `
  backend/tests/test_hybrid_retrieval.py `
  backend/tests/test_rag_security.py `
  backend/tests/test_release_scenarios.py `
  backend/tests/test_ticket_workflow.py -q

python -m ruff check backend
python -m compileall backend\app backend\scripts

cd frontend
npm run build
```

## 公开版文档

- [功能核对表](docs/A-v1.0_public_feature_audit.md)
- [发布说明](docs/A-v1.0_public_release.md)
- [测试结果](docs/A-v1.0_测试结果.md)
- [Bad Cases 摘要](docs/A-v1.0_bad_cases.md)

## 发布仓库生成

当前研发仓库包含较多内部记录和本地产物。要生成可公开推送的干净仓库，可执行：

```powershell
python backend/scripts/create_public_release_repo.py --target ..\project-a-rag-platform-public --force
```

该脚本会按白名单复制公开版文件，不会带上当前仓库的 Git 历史。
