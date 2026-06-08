# Release Notes — v1.0.0-rc.1

**发布日期：** 2026-06-01
**版本标签：** v1.0.0-rc.1

---

## 概述

Project A 企业设备售后诊断与工单闭环 RAG 平台的首个 Release Candidate。本版本完成了从 MVP 到生产就绪的完整演进，涵盖安全基线、可观测性、部署管理、异步任务、前端产品化和 E2E 测试六大阶段。

---

## 主要变更

### Phase 0：基线保护与环境收口

- 项目结构清点与技术栈确认
- CI/CD 基线建立（GitHub Actions）
- 本地验证命令标准化

### Phase 1：安全基线与配置校验

- 启动时配置校验：必填环境变量类型和范围检查
- 统一错误响应：所有 API 返回统一 JSON 格式
- 上传安全：文件类型白名单 + 大小限制（默认 10MB，最大 100MB）
- CORS 收紧：生产环境限制允许的 Origin
- API Key 常量时间比较：使用 `hmac.compare_digest` 替代 `==`
- 认证框架：X-API-Key 角色层级（viewer < operator < admin），默认关闭

### Phase 2：可观测性与审计

- request_id middleware：每个请求分配唯一 ID，贯穿日志和响应头
- 结构化日志：JSON 格式日志，统一日志级别和字段
- 审计日志：关键操作（文档入库/上传、工单创建/恢复/关闭、评测运行）持久化审计记录
- admin audit API：`GET /api/v1/admin/audit/events`（admin 角色限制）
- RAG trace request_id：RAG 问答链路 trace 元数据携带 request_id

### Phase 3：部署与数据管理

- 轻量 schema version：`schema_migrations` 表 + `CURRENT_SCHEMA_VERSION`
- Docker Compose 分离：`docker-compose.yml`（production）+ `docker-compose.demo.yml`（demo）
- Dockerfile 非 root 用户：appuser，`/app/data` 可写
- `.env.production.example`：生产推荐配置模板
- 部署文档：`docs/deployment_guide.md`

### Phase 4：异步任务与评测闭环

- Job 模型与存储：JobRecord、jobs 表、upsert/get/list 方法
- JobService：daemon thread 执行，PENDING → RUNNING → SUCCEEDED/FAILED 状态流转
- 异步入库接口：`POST /api/v1/jobs/ingest`（operator 角色）
- 异步评测接口：`POST /api/v1/jobs/evaluations`（admin 角色）
- Job 查询接口：`GET /api/v1/jobs/{job_id}`、`GET /api/v1/jobs`
- 审计闭环：job.succeeded / job.failed 审计事件

### Phase 5：前端产品化与运维控制台

- 前端结构重构：8 个页面级组件 + 共享组件（AppShell、ApiKeyConfig）
- API 客户端统一：`api/client.ts` 统一 axios 实例，自动注入 X-API-Key
- API 类型定义：`api/types.ts` 手动同步后端 schema（20+ 类型）
- API 端点封装：`api/endpoints.ts` 统一所有后端调用
- API Key 配置：ApiKeyConfig 组件，localStorage 持久化，角色选择
- 系统状态页面：展示 healthz / readyz / health 三个端点
- 资料管理页面：异步入库为主入口，同步入库标记为兼容
- Jobs 页面：任务列表、状态视觉区分、job_id 查询、RUNNING 自动轮询
- 审计日志页面：admin 权限限制，metadata 弹窗查看
- 诊断问答页面：单轮问答 + 多轮会话
- 验收中心页面：验收面板、trace 时间线、bad case 展示
- 构建优化：manualChunks 拆分，主应用 chunk 从 >500KB 降至 ~45KB

### Phase 5.1：前端生产收口

- demo 模式权限修复：未配置 API Key 时不强制禁用操作按钮
- UI 错误反馈补齐：所有页面错误均通过 el-alert 展示
- 写操作确认弹窗：8 个写操作均有确认弹窗
- activeTab 持久化：localStorage 存储，刷新恢复
- Jobs 页面收口：列表空状态、404 提示、error 截断
- Audit 页面收口：403 提示、metadata 截断、limit 可选

### Final RC：最终生产验收与发布收口

- 工作区清点：无误提交产物
- 全量验证：104 passed, ruff passed, frontend build passed, docker compose config passed
- 密钥安全检查：无真实密钥泄露
- 文档收口：deployment_guide.md、README.md 补充文档入口

### Final RC 1.1：验收脚本与交付可信度修正

- `final_acceptance.ps1` 修复：ProjectRoot 正确计算、中文路径编码、工具路径预检
- 脚本健壮性：Run-Step 函数封装、SUMMARY 汇总、失败 exit 1

### Final RC 1.2：验收脚本默认可用性与文档一致性收口

- 工具发现优先级：命令行参数 > 环境变量 > acceptance.defaults.json > PATH
- 中文路径编码：默认路径移入 acceptance.defaults.json
- 真实可执行预检：python / npm / docker / docker compose 版本检查

### RC 1.3：验收脚本配置可移植性修正

- acceptance.defaults.json 从 Git 跟踪移除，新增 acceptance.defaults.example.json
- .gitignore 加入 scripts/acceptance.defaults.json

### Stage 6：E2E 测试与前端可测试性

- Playwright 集成：8 个 spec 文件，21 个测试用例
- data-testid 注入：导航按钮、页面容器、输入框、操作按钮
- CI E2E smoke job：workflow_dispatch 触发

---

## API 端点汇总

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | /healthz | 无 | 存活检查 |
| GET | /readyz | 无 | 就绪检查 |
| GET | /health | 无 | 兼容旧接口 |
| GET | /api/v1/system/status | viewer | 系统状态 |
| GET | /api/v1/acceptance/overview | viewer | 验收概览 |
| POST | /api/v1/documents/ingest | operator | 同步入库 |
| POST | /api/v1/documents/upload | operator | 上传文档 |
| POST | /api/v1/chat | viewer | 单轮问答 |
| POST | /api/v1/chat/session | viewer | 多轮会话 |
| POST | /api/v1/chat/stream | viewer | 流式问答 |
| POST | /api/v1/tickets/start | operator | 启动工单 |
| POST | /api/v1/tickets/{id}/resume | operator | 人工确认 |
| POST | /api/v1/tickets/{id}/close | operator | 关闭工单 |
| GET | /api/v1/tickets | viewer | 工单列表 |
| POST | /api/v1/evaluations/run | admin | 同步评测 |
| GET | /api/v1/admin/audit/events | admin | 审计日志 |
| POST | /api/v1/jobs/ingest | operator | 异步入库 |
| POST | /api/v1/jobs/evaluations | admin | 异步评测 |
| GET | /api/v1/jobs/{id} | viewer | 查询 Job |
| GET | /api/v1/jobs | viewer | Job 列表 |

---

## 已知限制

- JobService 使用单进程 daemon thread，不适合多副本部署
- 前端类型定义手动同步，可引入 openapi-typescript 自动化
- element-plus 未按需加载，vendor chunk 较大（~922KB）
- 前端使用 tab 状态切换，未引入 vue-router
- start_demo_stack.ps1 依赖 PATH 中的 python 命令

---

## 升级说明

本版本为首个 RC，无需从旧版本升级。从零开始部署请参考 `docs/deployment_guide.md`。
