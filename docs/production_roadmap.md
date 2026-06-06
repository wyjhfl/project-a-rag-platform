# 生产化路线图（Production Roadmap）

> Phase 0：基线保护与环境收口 — 2026-05-28

---

## 1. 当前项目状态摘要

### 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI |
| 前端框架 | Vue 3 + Vite + TypeScript |
| RAG 编排 | LangChain / LangGraph |
| 默认向量存储 | Chroma |
| 默认结构化存储 | SQLite |
| 工单状态机 | LangGraph |
| 测试 | pytest |
| CI | GitHub Actions（Ubuntu + Python 3.11 + Node 20） |
| 容器编排 | Docker Compose（企业增强栈：PostgreSQL + Redis + Milvus） |

### 已完成能力

- 文本真实 LLM 主链：`deepseek_chat` 已通过 grounded 验收
- 多模态验收：Vision LLM 已转绿
- 多模态解析：MinerU Linux sliced 已转绿
- 前端演示中心：可展示 provider、多模态、evaluation、bad case、trace 时间线和原始 JSON
- 本地 demo：一键启动 / 停止脚本（PowerShell）
- 真实评测扩容：回归 30/30，对抗 20/20
- RAGAS 风格指标：context_precision=0.8667、faithfulness=0.6983、context_recall=0.9778
- 认证框架：X-API-Key 角色层级（viewer < operator < admin），默认关闭
- 健康检查：/healthz（liveness）、/readyz（readiness）、/health（legacy）
- Prompt 注入防护：PromptInjectionGuard，≥20 条最小测试用例
- 工单闭环：创建 → 需配件 → 需人工 → 恢复 → 关闭，幂等创建
- 公开发布脱敏：create_public_release_repo 脚本，路径/用户名自动替换

### 生产化缺口

- 前端无运维控制台：API Key 输入、错误展示等运维操作无 UI（Phase 5）

---

## 2. 本地验证命令

> 以下命令适用于 Windows 本地环境，使用绝对路径避免 python / npm alias 问题。

### 后端核心测试

```powershell
D:\codex安装\tools\Python312\python.exe -m pytest backend/tests/test_api.py backend/tests/test_auth.py backend/tests/test_health_readiness.py -q
```

### 前端构建

```powershell
cd frontend
D:\codex安装\tools\nodejs\npm.cmd run build
```

### Docker 配置检查

```powershell
docker compose config
```

### CI 全量测试（可选，本地复现 CI）

```powershell
D:\codex安装\tools\Python312\python.exe -m pytest ^
  backend/tests/test_api.py ^
  backend/tests/test_acceptance_overview_api.py ^
  backend/tests/test_auth.py ^
  backend/tests/test_enterprise_api.py ^
  backend/tests/test_hybrid_retrieval.py ^
  backend/tests/test_health_readiness.py ^
  backend/tests/test_rag_security.py ^
  backend/tests/test_release_scenarios.py ^
  backend/tests/test_ticket_workflow.py ^
  backend/tests/test_public_release_sanitization.py -q
```

### Ruff 代码检查

```powershell
D:\codex安装\tools\Python312\python.exe -m ruff check backend
```

---

## 3. CI 与本地差异

### 环境差异

| 维度 | CI（GitHub Actions） | 本地（Windows） |
|---|---|---|
| 操作系统 | Ubuntu Latest | Windows |
| Python 版本 | 3.11 | 3.12 |
| Node 版本 | 20 | 可能不同 |
| Python 路径 | `python`（系统 PATH） | `D:\codex安装\tools\Python312\python.exe` |
| npm 路径 | `npm`（系统 PATH） | `D:\codex安装\tools\nodejs\npm.cmd` |
| 依赖安装 | `pip install -e .` + `pytest ruff` | 需手动确认 venv 或全局安装 |
| 前端依赖 | `npm ci`（基于 package-lock.json） | `npm install` |

### 核心 Smoke Tests（适合 CI 和本地）

以下测试不依赖外部 LLM 服务，使用 sqlite + chroma + tmp_path，可在任何环境运行：

| 测试文件 | 覆盖范围 | 外部依赖 |
|---|---|---|
| test_api.py | 核心聊天、入库、拒答 | 无 |
| test_auth.py | API Key 认证与角色 | 无 |
| test_health_readiness.py | 健康检查端点 | 无 |
| test_acceptance_overview_api.py | 验收中心聚合接口 | 无 |
| test_enterprise_api.py | 企业增强接口（LLM 禁用场景） | 无 |
| test_hybrid_retrieval.py | BM25 / RRF / Reranker | 无 |
| test_rag_security.py | Prompt 注入防护 | 无 |
| test_ticket_workflow.py | 工单状态机闭环 | 无 |
| test_public_release_sanitization.py | 脱敏脚本 | 无 |

### 可能依赖外部服务或环境变量的测试

| 测试文件 | 依赖说明 |
|---|---|
| test_release_scenarios.py | 依赖 `data/real_manuals_sanitized/` 和 `data/eval/release_scenarios_v1.json`，不依赖外部 LLM，但依赖数据文件存在 |
| test_av13_acceptance.py | 版本验收测试，不在 CI 中 |
| test_av23_paddleocr_compatibility.py | PaddleOCR 兼容性测试，不在 CI 中 |
| test_av24_provider_comparison.py | Provider 对比测试，不在 CI 中 |

---

## 4. 后续生产化路线

### Phase 1：安全基线与配置校验

- 配置校验：启动时校验必填环境变量类型和范围
- 统一错误响应：所有 API 返回统一 JSON 错误格式
- 上传安全：文件类型白名单 + 大小限制
- CORS 收紧：生产环境限制允许的 Origin
- API Key 常量时间比较：使用 `hmac.compare_digest` 替代 `==`

### Phase 2：可观测性与审计

- [x] request_id middleware：每个请求分配唯一 ID，贯穿日志和响应头，ContextVar 生命周期管理，异常路径日志记录
- [x] 结构化日志：JSON 格式日志，统一日志级别和字段，幂等 handler 添加，settings.log_level 驱动
- [x] 审计日志：关键操作（文档入库/上传、工单创建/恢复/关闭、评测运行）持久化审计记录，敏感字段脱敏，list/tuple 递归处理
- [x] admin audit API：管理员可查询审计事件，admin 角色限制
- [x] RAG trace request_id：RAG 问答链路 trace 元数据携带 request_id，与请求链路关联

### Phase 3：部署与数据管理

- [x] 轻量 schema version：schema_migrations 表 + CURRENT_SCHEMA_VERSION，重复初始化安全
- [x] Docker Compose 分离：docker-compose.yml（production 企业栈）+ docker-compose.demo.yml（SQLite + Chroma 本地 demo）
- [x] Dockerfile 非 root 用户：appuser，/app/data 可写
- [x] .env.production.example：生产推荐配置模板，不含真实密钥
- [x] 部署文档：docs/deployment_guide.md，覆盖 demo/production 启动、健康检查、数据持久化、升级/回滚步骤

### Phase 4：异步任务与评测闭环

- [x] Job 模型与存储：JobRecord、jobs 表、upsert/get/list 方法
- [x] JobService：daemon thread 执行，PENDING → RUNNING → SUCCEEDED/FAILED 状态流转
- [x] 异步入库接口：POST /api/v1/jobs/ingest（operator 角色）
- [x] 异步评测接口：POST /api/v1/jobs/evaluations（admin 角色）
- [x] Job 查询接口：GET /api/v1/jobs/{job_id}（viewer）、GET /api/v1/jobs（viewer）
- [x] 审计记录：job.create 审计事件
- [x] 审计闭环：job.succeeded / job.failed 审计事件，回调机制，_safe_error 安全摘要
- [x] 同步接口兼容：/api/v1/documents/ingest 和 /api/v1/evaluations/run 不变
- [x] 评测逻辑提取：_run_evaluation_sync helper 复用

### Phase 5：前端产品化与运维控制台

- [x] 前端结构重构：App.vue 拆分为页面级组件（8 个页面）+ 共享组件（AppShell、ApiKeyConfig）
- [x] API 客户端统一：api/client.ts 统一 axios 实例，自动注入 X-API-Key，统一错误解析（error.message + error.code + request_id）
- [x] API 类型定义：api/types.ts 手动同步后端 schema（ErrorResponse、JobRecord、AuditEvent 等 20+ 类型）
- [x] API 端点封装：api/endpoints.ts 统一所有后端调用，含 Jobs、Audit、Health 等新端点
- [x] API Key 配置：ApiKeyConfig 组件，localStorage 持久化，角色选择（viewer/operator/admin），未配置时提示
- [x] 权限体验：根据角色区分 viewer/operator/admin 能力，401/403 展示清晰错误含 request_id
- [x] 系统状态页面：展示 /healthz、/readyz、/health 三个端点，readyz 失败展示非敏感错误，手动刷新
- [x] 资料管理页面：异步入库（POST /api/v1/jobs/ingest）为主入口，同步入库标记为兼容旧接口，上传反馈含 request_id
- [x] Jobs 页面：任务列表、状态视觉区分（PENDING/RUNNING/SUCCEEDED/FAILED）、job_id 查询、RUNNING 自动轮询
- [x] 审计日志页面：调用 /api/v1/admin/audit/events，403 提示需 admin 权限，metadata 弹窗查看（截断过长内容）
- [x] 工单页面：保留 start/resume/close 闭环，写操作反馈含 request_id
- [x] 评测中心页面：异步评测（POST /api/v1/jobs/evaluations）为主入口，同步评测标记为兼容，403 提示需 admin
- [x] 验收中心页面：保留原有验收面板、trace 时间线、bad case 展示
- [x] 诊断问答页面：保留问答和多轮会话，统一错误处理
- [x] 构建优化：manualChunks 拆分 vendor-vue/vendor-element/vendor-axios，主应用 chunk 从 >500KB 降至 ~45KB
- [x] 前端 build 通过：vue-tsc + vite build 成功

### Phase 5.1：前端生产收口与最终验收准备

- [x] demo 模式权限修复：未配置 API Key 时不强制禁用操作按钮，由后端决定 401/403
- [x] UI 错误反馈补齐：所有页面错误均通过 el-alert 展示，消除 console.error-only 路径
- [x] 写操作确认弹窗：异步入库、同步入库、上传、异步评测、同步评测、启动工单、人工确认、关闭工单
- [x] activeTab 持久化：localStorage 存储 project_a_active_tab，刷新恢复，白名单校验
- [x] API Key 配置收口：明确角色仅作 UI 提示，实际权限由后端判定，401/403 引导检查 API Key
- [x] Jobs 页面收口：列表空状态、job_id 404 提示、error 截断 300 字符、result 摘要不过长、轮询清理
- [x] Audit 页面收口：403 提示需 admin Key、metadata 截断、空状态、request_id 为空显示 "—"、limit 可选 50/100/200

### Final RC：最终生产验收与发布收口

- [x] 工作区清点：无误提交产物，frontend/src/api.ts 删除符合预期
- [x] 全量验证：104 passed, ruff passed, frontend build passed, docker compose config passed
- [x] 密钥安全检查：无真实密钥泄露，.env.production.example 增加 WARNING 注释
- [x] 文档收口：deployment_guide.md schema version 更新，README.md 补充文档入口链接
- [x] CI 配置检查：包含 Phase 1-4 测试、frontend build、ruff、docker compose config

### Final RC 1.1：验收脚本与交付可信度修正

- [x] final_acceptance.ps1 修复：ProjectRoot 正确计算（scripts 上一级）、中文路径编码、工具路径预检、Docker 必检
- [x] 脚本健壮性：Run-Step 函数封装、SUMMARY 汇总、失败 exit 1
- [x] 文档同步：final_acceptance_checklist.md 增加验收脚本用法说明

### Final RC 1.2：验收脚本默认可用性与文档一致性收口

- [x] 工具发现优先级：命令行参数 > 环境变量 > acceptance.defaults.json > PATH（跳过 WindowsApps alias）
- [x] 中文路径编码：默认路径移入 acceptance.defaults.json，脚本用 Get-Content -Encoding UTF8 读取
- [x] 真实可执行预检：python --version、npm --version、docker --version、docker compose version
- [x] SUMMARY 固定顺序：OrderedDictionary 保证 Backend > Ruff > Frontend > Docker Prod > Docker Demo
- [x] 文档一致性：final_acceptance_checklist.md 明确 Docker 必检、工具发现优先级、acceptance.defaults.json 说明

### RC 1.3：验收脚本配置可移植性修正 + Release Notes + Tag

- [x] acceptance.defaults.json 从 Git 跟踪移除，新增 acceptance.defaults.example.json（placeholder 路径）
- [x] .gitignore 加入 scripts/acceptance.defaults.json
- [x] final_acceptance.ps1 保持对本地 acceptance.defaults.json 的读取支持（如存在则读取，不存在则走参数/环境变量/PATH）
- [x] final_acceptance_checklist.md 说明本地 defaults 文件不提交、从 example 复制、参数运行方式
- [x] 新增 release notes：docs/release_notes_v1.0.0_rc1.md
- [x] 创建 annotated tag：v1.0.0-rc.1

### Stage 6：E2E 测试与前端可测试性

- [x] Playwright 集成：@playwright/test 安装，playwright.config.ts 配置（chromium only，30s timeout，trace + screenshot）
- [x] E2E 脚本：8 个 spec 文件覆盖验收中心、系统状态、API Key 配置、资料管理、异步任务、审计日志、工单闭环、评测中心
- [x] data-testid 注入：AppShell 导航按钮、API Key 配置按钮、各页面容器、输入框、操作按钮均添加 data-testid
- [x] CI E2E smoke job：workflow_dispatch 触发，构建 → preview → playwright test，独立 job 不阻塞主 CI
- [x] E2E 测试指南：docs/e2e_guide.md，覆盖目标、前置条件、运行命令、环境变量、测试覆盖表、常见失败原因、CI 集成建议、data-testid 参考表

### Production Landing Sprint：生产落地

- [x] Job 外部队列：DB-backed lease worker，支持 claim/complete/fail/heartbeat/cancel/timeout
- [x] Job 状态扩展：PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED/RETRYING
- [x] Job 重试机制：retry_count/max_retries，失败后 RETRYING，超过重试次数 FAILED
- [x] Job 取消接口：POST /api/v1/jobs/{job_id}/cancel，角色权限控制
- [x] Job 超时检测：timeout_stale_jobs 标记超时 job
- [x] 外部 worker：python -m app.job_worker，支持 WORKER_ID/JOB_POLL_INTERVAL_SECONDS/JOB_DEFAULT_TIMEOUT_SECONDS
- [x] Demo fallback：JOB_EXECUTION_MODE=inprocess（默认），production 使用 worker
- [x] 数据库迁移：python -m app.migrations status/upgrade，版本化、幂等、SQLite/PostgreSQL 双支持
- [x] 限流中间件：RateLimitMiddleware，429 响应，健康检查豁免，API Key hash 作为 key
- [x] Metrics 端点：GET /metrics，Prometheus text format，request/job/error 指标
- [x] 密钥扫描：scripts/secret_scan.py，CI 集成
- [x] OpenAPI 类型生成：scripts/export_openapi.py + npm run api:types
- [x] Docker worker service：production compose 增加 worker，demo 不强制
- [x] 文档收口：deployment_guide.md、release_notes_v1.0.0_production.md、production_roadmap.md 更新
- [x] Store-level atomic job claim
- [x] Worker supports evaluation.run
- [x] Rate limiter enforces both RPM and burst
- [x] Metrics integrated with request/job middleware
- [x] Cancel semantics: PENDING/RETRYING → CANCELLED directly
- [x] Audit events: job.claimed, job.retrying, job.timeout, job.cancelled
- [x] generated.ts committed to repo
- [x] Docker mandatory in final acceptance

### v1.0.0 Release Gate ✅ DONE

- [x] v1.0.0 正式发布：所有 Phase 0–5.1 + Final RC + RC 1.1–1.3 + Stage 6 + Production Landing 已完成
- [x] 全量验证通过：104 passed, ruff passed, frontend build passed, docker compose config passed
- [x] 无真实密钥泄露
- [x] Release Notes 已发布：docs/release_notes_v1.0.0.md

### Post-v1.0 Sprint 1：Redis Rate Limit + Worker Stress

- [x] Redis-backed rate limiting: MemoryRateLimiter + RedisRateLimiter (Lua script)
- [x] PostgreSQL worker stress validation: 50 jobs / 6 workers, 0 duplicates
- [x] Redis rate limit smoke: 7/7 PASSED (Docker Redis)
- [x] PostgreSQL job smoke: 10/10 PASSED (Docker PostgreSQL)
- [x] Final production acceptance: 13 steps including Redis/PostgreSQL smoke

### Production Recovery Sprint：Consistency Fix

- [x] JobService API unified: claim_job, complete_job (bool), fail_job (bool), cancel_running_job (bool)
- [x] SqliteStore: upsert_job, atomic claim_next_job (BEGIN IMMEDIATE)
- [x] Missing modules restored: job_worker.py, migrations.py
- [x] Metrics: Prometheus-style naming (project_a_request_total, etc.)
- [x] Secret scan: OpenAI key pattern detection, skip test files
- [x] PowerShell 5 compatibility: no `??` operators
- [x] Redis smoke clean output: no traceback, no absolute paths
- [x] Full E2E auto-start: backend + frontend preview + Playwright + cleanup

### Production Recovery Sprint 1.1：Test Coverage Restoration

- [x] 13 test files restored from recovered backup (3 → 16 files)
- [x] SqliteStore methods: add_document, add_chat_record, add_token_usage, upsert_ticket, get_ticket, get_ticket_by_idempotency_key, list_tickets
- [x] Readyz: optional dep failure → 200 degraded (not 503)
- [x] Acceptance overview: provider panel returns "passed" when LLM configured
- [x] Backend scripts restored: create_public_release_repo, run_av13/av23/av24, run_provider_acceptance
- [x] 147 passed, 1 warning — all green

### v1.0.1 RC 1 — Release Metadata

- [x] Release notes: docs/release_notes_v1.0.1_rc1.md
- [x] Release lineage notice: docs/release_lineage_notice.md
- [x] README: v1.0.1-rc.1 entry + Git lineage notice
- [x] Roadmap: v1.0.1 RC 1 completion items
- [x] Final production acceptance: 13/13 PASSED
- [x] RC tag: v1.0.1-rc.1

---

## 5. 验收标准

- [x] 后端核心测试通过：7 个测试文件 — **104 passed**（2026-05-31 本地验证）
- [x] 前端 build 通过：`npm run build` — **vue-tsc + vite build 成功，12.36s**（2026-05-31 本地验证）
- [x] ruff check 通过：**All checks passed**（2026-05-31 本地验证）
- [x] docker compose config 通过：**production + demo 两个配置均通过**（2026-05-31 本地验证）
- [x] 不泄露真实密钥：代码和文档中无硬编码 API Key
- [x] 不破坏 demo 默认路径：`start_demo_stack.ps1` 仍可正常启动

---

## 6. 风险与后续项

### 版本描述不一致

| 问题 | 详情 |
|---|---|
| README 版本 vs pyproject.toml 版本 | README 提到 `v3.5-public-delivery` 和 `A-v3.6 Release Tag`，pyproject.toml version 为 `1.0.0`，语义不同但无冲突（前者是发布 tag，后者是包版本） |
| CI Python 版本 vs 本地 | CI 使用 Python 3.11，本地使用 Python 3.12，numpy 约束 `>=2.3,<2.4` 可能在 3.11 上有兼容性问题 |

### 测试与依赖风险

| 问题 | 详情 |
|---|---|
| start_demo_stack.ps1 使用 `python` alias | 脚本中 `Start-Process -FilePath "python"` 依赖 PATH 中的 python，Windows 环境可能找不到 |
| 前端 chunk 过大 | Phase 5 已通过 manualChunks 拆分，主应用 chunk 降至 ~45KB；element-plus 自身 ~922KB 为库大小 |
| JobService 单进程线程模型 | 当前使用 daemon thread，适合 MVP；分布式/多副本部署需外部队列（Celery/RQ） |
| test_release_scenarios.py 依赖数据文件 | 需要 `data/real_manuals_sanitized/` 目录存在且包含 ≥5 个文件，CI 中通过 checkout 保证，本地需确认 |
| test_public_release_sanitization.py 路径 hack | 使用 `sys.path.insert(0, str(PROJECT_DIR))` 然后 `from backend.scripts...`，在 pytest 的 pythonpath 配置下可能行为不一致 |
| 前端 preview 端口不一致 | package.json 中 `preview` 端口为 4173，start_demo_stack.ps1 使用 4175 |

### 不在本阶段解决的问题

- start_demo_stack.ps1 的 python alias 问题（需确认是否影响 demo 启动）
- 前端端口不一致问题
- numpy 版本约束在 Python 3.11 上的兼容性

### 仍未完成的生产增强

- ~~真实外部队列：JobService 当前使用 daemon thread，多副本部署需 Celery/RQ/Redis Queue~~ → Production Landing 已实现 DB-backed lease worker
- ~~多副本 Job 调度：当前单进程，无法跨实例协调~~ → Production Landing 已实现 claim/lease 机制
- ~~前端自动 OpenAPI 类型生成：当前手动同步 types.ts，可引入 openapi-typescript~~ → Production Landing 已实现
- ~~前端 E2E 测试：当前无前端测试脚本~~ → Stage 6 已完成，8 个 spec 文件 + Playwright 集成
- element-plus 按需加载：可进一步通过 unplugin-vue-components 减小 vendor chunk
- 前端 vue-router：当前使用 tab 状态切换，可引入 vue-router 支持 URL 路由

### 本地环境验证发现

| 问题 | 详情 |
|---|---|
| 本地 Python 无项目依赖 | `D:\codex安装\tools\Python312\python.exe` 是裸安装，无 fastapi/chromadb/pytest 等，需 `pip install -e .` 后才能运行测试 |
| 沙箱限制 pip 全局安装 | Windows 沙箱阻止写入 `C:\Users\Administrator\AppData\Roaming\Python` 和 Python 安装目录的 `__pycache__`，需使用 `--target=.pip_local` + `PYTHONPATH` 绕过 |
| Docker compose config | production + demo 两个配置均已在本地验证通过（2026-05-31） |
| 前端需先 npm install | `npm run build` 前需执行 `npm install`，CI 使用 `npm ci`（基于 package-lock.json） |
| 网络下载慢 | chromadb（23.5MB）、onnxruntime（13MB）等大包下载缓慢，首次安装耗时较长 |
