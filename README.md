# Project A：企业设备售后诊断与工单闭环 RAG 平台

[![CI](https://github.com/wyjhfl/project-a-rag-platform/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/wyjhfl/project-a-rag-platform/actions/workflows/ci.yml)

Project A 是一个面向简历与技术面试展示的 **企业设备售后诊断 RAG 平台**。它不是只包装聊天接口，而是把设备故障诊断做成“可检索、可引用、可评测、可追踪、可运维”的 AI 应用工程闭环。

```text
故障描述 / 设备型号 / 故障码
-> 文档入库与混合检索
-> grounded 回答 + 引用证据
-> 安全拒答 / 人工工单升级
-> 异步 Jobs / Evaluation / Audit / Metrics
-> CI + E2E + Docker + 生产验收门禁
```

## 30 秒面试开场白

> 我做的 Project A 是企业设备售后诊断 RAG 平台。它能把设备型号、故障码和现场现象转成带引用的排障建议；当资料不足或操作高风险时，会拒答或升级人工工单。工程上我做了 FastAPI 后端、Vue 运维控制台、异步 Job、审计日志、Prometheus metrics、OpenAPI 类型同步、Playwright E2E、Docker Compose 和最终生产验收脚本，所以它不是一个“能聊”的 demo，而是一个能展示生产化思维的 RAG 项目。

## 简历 bullet

- **中文**：企业设备售后诊断 RAG 平台，基于 FastAPI、Vue 3、Chroma/SQLite、LangChain/LangGraph 实现带引用的故障诊断问答、Prompt 注入防护、异步入库/评测任务、工单闭环、审计日志、Prometheus metrics、OpenAPI 类型同步与 Playwright E2E；通过 13 步生产验收脚本覆盖 pytest、ruff、前端构建、Docker Compose、Redis 限流 smoke、PostgreSQL worker stress 与 Full E2E。
- **English**：Built an enterprise equipment after-sales diagnosis RAG platform with FastAPI, Vue 3, Chroma/SQLite, LangChain/LangGraph, grounded answers with citations, prompt-injection guardrails, async ingestion/evaluation jobs, ticket escalation, audit logs, Prometheus metrics, OpenAPI-generated frontend types, Playwright E2E, and a 13-step production acceptance gate.

## 面试官 5 分钟看什么

1. **业务闭环**：资料入库 -> RAG 问答 -> 引用证据 -> 拒答边界 -> 工单升级。
2. **工程闭环**：异步 Job、审计日志、Request ID、Metrics、统一错误体。
3. **质量闭环**：pytest、ruff、OpenAPI drift guard、Playwright E2E、secret scan、Docker config、PostgreSQL/Redis smoke。
4. **生产取舍**：SQLite/Chroma 支持轻量 demo，PostgreSQL/Redis/Milvus compose 支持企业增强路径。
5. **可解释边界**：高风险、资料不足、OCR/多模态能力边界都有明确说明。

## 当前发布版本

- Production release tag: `v1.0.4`
- Hosted repository: `https://github.com/wyjhfl/project-a-rag-platform`
- Release notes: [docs/release_notes_v1.0.4.md](docs/release_notes_v1.0.4.md)
- Release lineage notice: [docs/release_lineage_notice.md](docs/release_lineage_notice.md)

> 注意：当前生产线基于重建后的 Git 历史，已在 release notes 和 lineage notice 中透明说明。面试展示时重点讲工程能力与验收证据，不把 reconstructed lineage 表述为原始连续历史。

## 作品集与面试材料

- Resume / interview showcase: [docs/resume_interview_showcase.md](docs/resume_interview_showcase.md)
- 5-10 分钟面试 Demo 脚本: [docs/interview_demo_script.md](docs/interview_demo_script.md)
- 面试追问答法: [docs/interview_questions.md](docs/interview_questions.md)
- Architecture overview: [docs/architecture_overview.md](docs/architecture_overview.md)
- Demo guide: [docs/demo_guide.md](docs/demo_guide.md)
- E2E guide: [docs/e2e_guide.md](docs/e2e_guide.md)
- Production deployment guide: [docs/deployment_guide.md](docs/deployment_guide.md)
- Final production acceptance checklist: [docs/final_acceptance_checklist.md](docs/final_acceptance_checklist.md)
- Enterprise landing checklist: [docs/enterprise_landing_checklist.md](docs/enterprise_landing_checklist.md)
- Production roadmap: [docs/production_roadmap.md](docs/production_roadmap.md)

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI, Pydantic, pytest, ruff |
| 前端 | Vue 3, Vite, TypeScript, Element Plus, Playwright |
| RAG | LangChain / LangGraph, Chroma, 混合检索与 rerank 边界 |
| 存储 | SQLite demo 路径，PostgreSQL production smoke 路径 |
| 异步任务 | JobService / Worker claim / cancel / retry / timeout / heartbeat |
| 安全 | X-API-Key 角色、PromptInjectionGuard、上传安全、secret scan |
| 可观测性 | Request ID、结构化错误、审计日志、Prometheus `/metrics` |
| 生产验证 | Docker Compose、Redis rate limit smoke、PostgreSQL worker stress、final acceptance |

## 快速启动 Demo

推荐用一键 E2E demo runner 启动后端和前端 preview，并自动跑 Playwright 主路径：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_full_e2e_demo.ps1 `
  -PythonExe "D:\path\to\Python312\python.exe" `
  -NpmCmd "D:\path\to\nodejs\npm.cmd"
```

默认地址：

- 前端控制台：[http://127.0.0.1:4173](http://127.0.0.1:4173)
- 后端 healthz：[http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz)
- 后端 readyz：[http://127.0.0.1:8000/readyz](http://127.0.0.1:8000/readyz)
- Metrics：[http://127.0.0.1:8000/metrics](http://127.0.0.1:8000/metrics)

如果只想手动启动：

```powershell
# terminal 1
$env:AUTH_ENABLED="false"
$env:STORAGE_BACKEND="sqlite"
$env:VECTOR_BACKEND="chroma"
$env:RATE_LIMIT_ENABLED="false"
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# terminal 2
cd frontend
npm run build
$env:VITE_API_BASE="http://127.0.0.1:8000"
npm run preview
```

## 最终生产验收

Production releases use `scripts/final_production_acceptance.ps1` as the single final gate. It covers backend tests, ruff, frontend build, OpenAPI types, E2E list, secret scan, Docker Compose validation, PostgreSQL smoke, Redis smoke, worker stress, and optional Full E2E.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\final_production_acceptance.ps1 `
  -PythonExe "D:\path\to\Python312\python.exe" `
  -NpmCmd "D:\path\to\nodejs\npm.cmd" `
  -RunFullE2E
```

## 推荐演示顺序

1. 打开前端控制台 Acceptance 页，先讲“面试展示入口”卡片。
2. Quality：集中讲 RAG 指标、Bad Case、Trace 复盘和工程取舍。
3. System Status：展示 release、healthz/readyz、metrics、Request ID 错误排障。
4. Documents + Jobs：讲资料入库为什么要异步化，以及 cancel/retry/timeout 的生产语义。
5. Chat：讲 grounded answer、引用证据和 Prompt 注入防护。
6. Tickets：讲高风险或资料不足时如何升级人工闭环。
7. Evaluations：讲 RAG 评测和 bad case 复盘。
8. Audit：用审计日志和 Request ID 收束“可追踪、可运维”。
9. GitHub Actions / final acceptance：展示自动化验证证据。

## 仓库结构

```text
backend/app/        FastAPI API、RAG、Jobs、Audit、Rate Limit、Storage
backend/tests/      后端自动化测试
frontend/src/       Vue 运维控制台
frontend/e2e/       Playwright E2E smoke tests
docs/               面试材料、架构、部署、release notes、验收清单
scripts/            OpenAPI 导出、secret scan、smoke、最终验收脚本
```

## 核心接口

| 接口 | 说明 |
|---|---|
| `POST /api/v1/chat` | RAG 问答主入口 |
| `POST /api/v1/documents/ingest` | 同步资料入库 |
| `POST /api/v1/jobs/ingest` | 异步资料入库 Job |
| `POST /api/v1/jobs/evaluations` | 异步评测 Job |
| `GET /api/v1/jobs` | Job 列表和状态查询 |
| `GET /api/v1/audit/events` | 审计事件 |
| `GET /healthz` / `GET /readyz` | liveness / readiness |
| `GET /metrics` | Prometheus metrics |

## 认证与权限

生产模式通过 `X-API-Key` 做角色控制：

```text
viewer < operator < admin
```

- viewer：查询系统状态、Job、部分只读数据。
- operator：资料入库、普通运维操作。
- admin：评测、审计、敏感管理能力。

前端的角色选择只用于 UI 提示，真实权限以后端 API Key 校验为准。

## 后续优化方向

面试求职阶段优先做“可展示、可解释、可验证”的优化：

1. 继续补充真实业务样本和 bad case 复盘。
2. 增加更细的 RAG 指标趋势展示。
3. 引入 Grafana / OTel，把 `/metrics` 从文本端点升级为完整观测面板。
4. 用 Alembic 管理生产数据库迁移。
5. 将 JobService 演进为 Redis/RQ/Celery 等外部队列，实现多实例可扩展调度。
