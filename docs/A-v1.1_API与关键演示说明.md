# A-v1.1 API 与关键演示说明

## 1. 文档目的

这份文档不是完整接口手册，而是 A-v1.1 对外演示所需的最小 API 说明和演示路径说明。

目标有三个：

- 让陌生读者快速知道先看哪些接口。
- 让前端演示顺序和 API 主链一一对应。
- 让截图证据和接口状态有固定落点。

## 2. 核心接口

### 2.1 基础状态

- `GET /health`
  - 用途：确认服务在线和当前版本号。
  - 关键字段：`status`、`version`

- `GET /api/v1/system/status`
  - 用途：确认系统运行状态、LLM 配置状态、资料源和当前向量库状态。
  - 关键字段：`status`、`version`、`llm_enabled`、`llm_provider`、`llm_model`、`vector_store_ready`、`docs_sources`

### 2.2 资料管理

- `POST /api/v1/documents/ingest`
  - 用途：把 `seed_docs`、`real_manuals_sanitized` 或 `uploaded_docs` 入库到当前检索链。
  - 关键字段：`document_count`、`chunk_count`

- `POST /api/v1/documents/upload`
  - 用途：上传单个文档到 `uploaded_docs`。
  - 关键字段：`filename`、`path`

### 2.3 问答链路

- `POST /api/v1/chat`
  - 用途：普通问答、资料不足拒答、高风险问题安全后处理。
  - 关键字段：`answer`、`citations`、`llm_used`、`insufficient`、`safety_warning`

- `POST /api/v1/chat/session`
  - 用途：多轮指代消解。
  - 关键字段：`session_id`、`resolved_question`、`answer`、`citations`

- `POST /api/v1/chat/stream`
  - 用途：SSE 流式输出。
  - 验收方式：最后应返回 `data: [DONE]`

### 2.4 工单闭环

- `POST /api/v1/tickets/start`
  - 用途：启动售后工单流程。
  - 关键字段：`ticket.status`、`ticket.risk_level`、`next_action`

- `GET /api/v1/tickets`
  - 用途：查看当前工单列表。

- `POST /api/v1/tickets/{ticket_id}/resume`
  - 用途：人工确认后恢复工单。

- `POST /api/v1/tickets/{ticket_id}/close`
  - 用途：关闭工单。

### 2.5 评测入口

- `POST /api/v1/evaluations/run`
  - 用途：统一触发回归 / RAGAS / 对抗评测入口。
  - 边界：完整 RAGAS 和对抗报告仍以脚本输出为准。

## 3. 推荐演示顺序

建议演示顺序固定为：

1. 系统状态
2. 资料入库
3. 普通问答
4. 多轮会话
5. 高风险工单
6. 评测入口
7. Swagger / OpenAPI

这样演示的原因：

- 先证明服务活着。
- 再证明资料可进系统。
- 再证明问答不是空壳。
- 然后把业务闭环和工程验证带出来。

## 4. 典型请求路径

### 4.1 最小主链

```text
GET /health
GET /api/v1/system/status
POST /api/v1/documents/ingest {"docs_source":"real_manuals_sanitized"}
POST /api/v1/chat {"question":"A100 出现 E-17，排气温度升高，应该怎么排查？"}
```

### 4.2 多轮主链

```text
POST /api/v1/chat/session {"session_id":"enterprise-session","question":"A100 出现 E-17 报警怎么排查？"}
POST /api/v1/chat/session {"session_id":"enterprise-session","question":"它还能继续运行吗？"}
```

### 4.3 工单主链

```text
POST /api/v1/tickets/start {"question":"UPS-30K 电池有异味并冒烟，现场想重启。","idempotency_key":"demo-hitl"}
POST /api/v1/tickets/{ticket_id}/resume {"reviewer":"王工","decision":"approved"}
POST /api/v1/tickets/{ticket_id}/close {"closed_by":"李工"}
```

### 4.4 评测入口

```text
POST /api/v1/evaluations/run {
  "evaluation_type":"regression",
  "cases_path":"data/eval/real_regression_cases_v1.json",
  "docs_source":"real_manuals_sanitized"
}
```

## 5. 关键截图清单

本轮截图统一放在：

```text
docs/assets/a-v1.1/
```

建议保留的截图：

- `01-system-status.png`
  - 对应：Vue 系统状态页
  - 证明：版本、LLM 状态、模型名、向量库状态

- `02-chat-a100-e17.png`
  - 对应：A100 E-17 普通问答页
  - 证明：真实问答结果、引用来源、`llm_used`

- `03-ticket-hitl.png`
  - 对应：高风险工单页
  - 证明：`NEED_HUMAN`、HITL、列表刷新

- `04-evaluation-center.png`
  - 对应：评测中心页
  - 证明：评测入口存在、参数可配置

- `05-swagger-docs.png`
  - 对应：FastAPI Swagger
  - 证明：OpenAPI 对外可见

## 6. 当前关键截图对应状态

- 系统状态截图应看到 `version=v1.1`。
- 问答截图应看到 A100 E-17 相关回答和 `real_air_compressor_a100_faults.md` 引用。
- 工单截图应体现高风险问题进入人工确认链路。
- 评测中心截图应看到 `regression / ragas / adversarial` 三类入口。
- Swagger 截图应体现核心路由存在。

## 7. 相关证据文件

- [A-v1.1 验证记录](docs/A-v1.1_验证记录.md)
- [Vue + FastAPI 全功能测试记录](docs/A-vue-fastapi_full_test_record_2026-05-16.md)
- [严格预检 JSON](docs/A-vue-fastapi_preflight_2026-05-17.json)
