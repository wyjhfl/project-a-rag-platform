# A-v1.1 验证记录

## 1. 验证目标

A-v1.1 验证的不是新业务功能，而是“公开主链说法是否和当前仓库真实状态一致”。

本轮重点确认：

- 版本元信息已经从 `v1.0` 收敛到 `v1.1`。
- README、发布审查、功能核对和面试边界文档能互相对上。
- 公开主链接口仍然可用。
- 最新预检与手测证据能支撑 README 中的默认主链说法。

## 2. 静态复核结果

已复核内容：

- `README.md`
- `docs/A-v1.0_public_feature_audit.md`
- `docs/A-v1.0_发布审查文档.md`
- `docs/A-v1.1_教学说明.md`
- `docs/A-v1.1_面试讲法与版本边界说明.md`
- `docs/A-v1.1_API与关键演示说明.md`

复核结论：

- 正式演示主入口统一为 `FastAPI + Vue3`。
- 默认主链统一为 `SQLite + Chroma + 脱敏资料 + 核心 API`。
- Redis、PostgreSQL、Milvus、Neo4j、真实多模态统一描述为“可选增强”。
- 公开宣称的核心能力都能落到代码入口和至少一类证据材料。

## 3. 运行复验结果

### 3.1 严格预检

预检文件：

- [docs/A-v1.1_preflight_2026-05-18.json](docs/A-v1.1_preflight_2026-05-18.json)

关键结果：

- `health.passed=true`
- `system_status.passed=true`
- `direct_llm_call.passed=true`
- `ingest_real_manuals.passed=true`
- `strict_chat_llm.passed=true`
- `critical_failures=[]`

预检结论：

- 当前环境下，真实 LLM 调用和主链问答均可通过。
- `real_manuals_sanitized` 入库成功，记录为 `16 documents / 81 chunks`。
- 本轮预检显式采用“公开主链口径”运行：`sqlite + chroma + 关闭外部增强`。

### 3.2 环境偏差说明

同日还复现了一次“按当前终端残留环境直接运行”的失败现象：

- `STORAGE_BACKEND=postgres` 会让模块导入时先尝试连接 PostgreSQL。
- 旧的 `LLM_PROVIDER / LLM_BASE_URL` 残留环境变量会把真实 LLM 请求打到错误端点。

这说明：

- 公开主链验证和本机增强环境验证需要明确分开。
- A-v1.1 的结论应以 `A-v1.1_preflight_2026-05-18.json` 为准。

### 3.3 手测记录

手测文件：

- [docs/A-vue-fastapi_full_test_record_2026-05-16.md](docs/A-vue-fastapi_full_test_record_2026-05-16.md)

可复用结论：

- Vue3 企业工作台和 FastAPI API 可以共同支撑主链演示。
- 系统状态、资料入库、问答、工单、评测中心都有明确入口。
- 真实 LLM 曾出现环境变量覆盖问题，但已在预检脚本中修正为优先读取项目 `.env`。

## 4. 关键证据索引

默认主链：

- `backend/tests/test_api.py`
- `backend/tests/test_enterprise_api.py`
- `backend/tests/test_release_scenarios.py`
- `backend/tests/test_ticket_workflow.py`
- `docs/A-v1.0_测试结果.md`

发布边界：

- `docs/A-v1.0_发布审查文档.md`
- `docs/A-v1.0_public_feature_audit.md`
- `docs/A-v1.1_面试讲法与版本边界说明.md`

前端 / API 演示：

- `docs/A-v1.1_API与关键演示说明.md`
- `docs/A-v1.1_preflight_2026-05-18.json`
- `docs/A-vue-fastapi_preflight_2026-05-17.json`
- `docs/assets/a-v1.1/`

增强能力真实验收：

- `docs/A-v1.0_redis_真实缓存验收.md`
- `docs/A-v1.0_postgresql_真实存储验收.md`
- `docs/A-v1.0_neo4j_真实联网验收.md`
- `docs/A-v1.0_milvus_multimodal_真实验收.md`

## 5. 截图证据

截图目录：

```text
docs/assets/a-v1.1/
```

目标截图：

- `01-system-status.png`
- `02-chat-a100-e17.png`
- `03-ticket-hitl.png`
- `04-evaluation-center.png`
- `05-swagger-docs.png`

说明：

- 这些截图用于支撑 README 和 A-v1.1 API 文档中的演示顺序。
- 截图属于展示型证据，不替代自动化测试或 JSON 预检结果。
- 当前目录下已生成：
  - `01-system-status.png`
  - `02-chat-a100-e17.png`
  - `03-ticket-hitl.png`
  - `04-evaluation-center.png`
  - `05-swagger-docs.png`

## 6. 本轮结论

A-v1.1 的结论不是“又多了什么功能”，而是：

- 版本边界更清楚了。
- 默认主链与可选增强分层更清楚了。
- 证据链更集中、更容易被外部读者验证了。
- 公开导出脚本已经可以带上 A-v1.1 的新文档和截图资产。
