# Project A：企业设备售后诊断与工单闭环 RAG 平台

Project A 是一个面向 AI 大模型 / RAG 开发求职展示的企业设备售后诊断平台。

它不是只做“问答”的 RAG demo，而是围绕设备故障描述，完成：

```text
故障问题
-> 知识检索
-> grounded 回答
-> 引用证据
-> bad case / trace / evaluation
-> 工单与人工升级闭环
```

当前项目已经进入 **A-v3.6 Release Tag 收口阶段**：主链可本地演示，验收证据可追溯，前端演示中心可直接讲项目状态，真实评测样本已扩容并转绿，GitHub 远端 CI 已通过，README 已按招聘方、作品集和简历投递路径整理，并准备以 `v3.5-public-delivery` 作为公开交付版本。

## 作品集摘要

Project A 是一个企业设备售后诊断 RAG 平台，把设备型号、故障码和现场现象转成可引用的排障建议，并在资料不足或高风险操作时拒答/升级人工。项目覆盖 FastAPI、Vue、Chroma、SQLite、LangChain/LangGraph、Provider 验收、多模态边界、evaluation、bad case、trace 和工单闭环。A-v2.9 后真实回归扩容到 `30/30`、真实对抗扩容到 `20/20`，并达到 `context_precision=0.8667`、`faithfulness=0.6983`、`context_recall=0.9778`。

## 简历投递口径

- **简历 bullet**：企业设备售后诊断 RAG 平台，基于 FastAPI、Vue、Chroma、SQLite、LangChain/LangGraph 实现可引用问答、Provider 验收、多模态边界、bad case、trace、evaluation 与工单闭环；真实回归扩容至 `30/30`，真实对抗扩容至 `20/20`。
- **GitHub pinned repo**：Equipment after-sales diagnosis RAG platform with grounded answers, citations, evaluation, trace, provider acceptance, multimodal boundaries, and ticket workflow.
- **30 秒开场白**：我做的 Project A 不是普通聊天 demo，而是把设备故障诊断做成可检索、可引用、可评测、可追踪、可演示、能升级人工的 RAG 工程闭环。

完整投递材料见：[docs/A-v3.4-resume-delivery-pack.md](docs/A-v3.4-resume-delivery-pack.md)。

## 当前发布版本

- Release tag：`v3.5-public-delivery`
- Release notes：[docs/A-v3.6-public-release-notes.md](docs/A-v3.6-public-release-notes.md)
- 最终巡检：[docs/A-v3.5-final-remote-audit.md](docs/A-v3.5-final-remote-audit.md)
- **v1.0.1-rc.1 Release Notes**：[docs/release_notes_v1.0.1_rc1.md](docs/release_notes_v1.0.1_rc1.md)


- **v1.0.1 Release Notes**?[docs/release_notes_v1.0.1.md](docs/release_notes_v1.0.1.md)
- **v1.0.1 Release Artifacts**?[docs/release_artifacts_v1.0.1.md](docs/release_artifacts_v1.0.1.md)
- **Canonical Repo Decision**?[docs/canonical_repo_decision.md](docs/canonical_repo_decision.md)

### Git Lineage Notice

> **重要**：当前仓库的 Git 历史经历过 `.git` 目录损毁和重建。v1.0.0 tag 是 reconstructed tag，不是原始 `e64b095`。远程 origin 指向不同的公开交付仓库。详见 [docs/release_lineage_notice.md](docs/release_lineage_notice.md)。

## 30 秒看懂项目

- **业务场景**：企业设备售后诊断，输入设备型号、故障码或现场现象，输出带引用的排障建议，并在高风险或资料不足时触发拒答/人工升级。
- **核心能力**：RAG 检索、grounded 回答、引用证据、Provider 验收、多模态边界、bad case、trace、evaluation、工单闭环。
- **默认 demo**：`sqlite + chroma + deepseek-chat + FastAPI + Vue 演示中心`，不要求现场部署 PostgreSQL、Redis、Milvus、Neo4j 或 PaddleOCR。
- **质量证据**：真实回归 `30/30`，真实对抗 `20/20`，RAGAS 风格 `context_precision=0.8667`、`faithfulness=0.6983`、`context_recall=0.9778`。
- **面试亮点**：不是只包装聊天接口，而是把“能回答”推进到“可验收、可追踪、可解释边界、可本地演示”的 RAG 工程系统。

## 当前状态

推荐公开演示画像：

```text
sqlite + chroma + deepseek-chat + FastAPI + Vue 演示中心
```

已转绿能力：

- 文本真实 LLM 主链：`deepseek_chat` 已通过 grounded 验收。
- 多模态验收：`Vision LLM` 已转绿。
- 多模态解析：`MinerU Linux sliced` 已转绿。
- 前端演示中心：可展示 provider、多模态、evaluation、bad case、trace 时间线和原始 JSON。
- 本地 demo：已有一键启动和一键停止脚本。
- 真实评测扩容：回归 `30/30`，对抗 `20/20`，RAGAS 风格 `faithfulness=0.6983`、`context_precision=0.8667`、`context_recall=0.9778`。

明确边界：

- `MiMo` 已在 A-v2.2 通过 token-plan 口径重新验收，`mimo-v2.5-pro` 和 `mimo-v2.5` 均已进入 grounded 可比较状态。
- A-v2.4 横向对比后，`deepseek_chat` 仍推荐作为公开 demo 默认主链，`mimo-v2.5` 作为候选对照。
- `PaddleOCR` 已在 A-v2.3 正式定性为 runtime compatibility boundary，不进入默认 demo 路径。
- `.env` 偏企业增强开发口径，公开演示请使用 `.env.demo.example` / `.env.demo`。
- Redis、PostgreSQL、Milvus、Neo4j 等增强能力保留代码入口和部分验收证据，但不是公开 demo 默认前提。

## 快速启动 Demo

前置条件：

- Python 环境已可用。
- 前端依赖已安装，或可在 `frontend/` 下执行 `npm install`。
- `.env` 中存在真实 `DEEPSEEK_API_KEY`。

准备 demo 配置：

```powershell
copy .env.demo.example .env.demo
```

启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_demo_stack.ps1 -StopExisting
```

停止：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop_demo_stack.ps1
```

默认访问地址：

- 前端演示中心：[http://127.0.0.1:4175](http://127.0.0.1:4175)
- 后端健康检查：[http://127.0.0.1:18082/health](http://127.0.0.1:18082/health)
- 系统状态：[http://127.0.0.1:18082/api/v1/system/status](http://127.0.0.1:18082/api/v1/system/status)
- 验收中心接口：[http://127.0.0.1:18082/api/v1/acceptance/overview](http://127.0.0.1:18082/api/v1/acceptance/overview)

更完整的启动和排查说明见：[docs/demo_guide.md](docs/demo_guide.md)。

生产部署指南：[docs/deployment_guide.md](docs/deployment_guide.md)。
最终验收清单：[docs/final_acceptance_checklist.md](docs/final_acceptance_checklist.md)。
生产化路线图：[docs/production_roadmap.md](docs/production_roadmap.md)。
Release Notes：[docs/release_notes_v1.0.0_rc1.md](docs/release_notes_v1.0.0_rc1.md)。
- [v1.0.0 Release Notes](docs/release_notes_v1.0.0.md)
Production Release Notes：[docs/release_notes_v1.0.0_production.md](docs/release_notes_v1.0.0_production.md)。
E2E 测试指南：[docs/e2e_guide.md](docs/e2e_guide.md)。

## 最终验收脚本

一键运行全部验收检查（后端测试、ruff、前端构建、Docker compose 配置）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\final_acceptance.ps1
```

本地工具路径配置说明：
- `scripts/acceptance.defaults.json` 是本地私有配置，不提交到 Git。
- 可从 example 文件复制：`copy .\scripts\acceptance.defaults.example.json .\scripts\acceptance.defaults.json`，然后填入本机实际路径。
- 也可用参数运行：`powershell -ExecutionPolicy Bypass -File .\scripts\final_acceptance.ps1 -PythonExe "..." -NpmCmd "..."`

## 演示顺序

推荐按这个顺序讲 5-10 分钟：

1. 项目定位：设备售后诊断与工单闭环 RAG。
2. Demo 画像：`sqlite + chroma + deepseek-chat`。
3. 系统状态：确认后端、LLM、资料源、向量库状态。
4. 验收中心：讲 provider、多模态、evaluation、bad case。
5. 文本主链：讲 grounded 回答、引用和拒答边界。
6. 多模态边界：讲 Vision / MinerU 转绿，PaddleOCR 阻塞。
7. trace：展开低分 case 的关键输入输出和原始 JSON。
8. 收束：讲清默认 demo、候选 provider、OCR 边界和下一步面试材料压缩。

完整演示脚本见：[docs/demo_script.md](docs/demo_script.md)。

## 技术栈

- 后端：FastAPI
- 前端：Vue 3 + Vite + TypeScript
- RAG 编排：LangChain / LangGraph
- 默认向量存储：Chroma
- 默认结构化存储：SQLite
- 工单状态机：LangGraph
- 测试：pytest
- 演示中心：前端聚合 `/api/v1/acceptance/overview`

## 仓库结构

```text
backend/app/        FastAPI、RAG、工单、评测与验收接口
backend/scripts/    provider、多模态、前端联调等预检脚本
backend/tests/      自动化测试
frontend/           Vue 演示中心
data/               seed data、真实脱敏资料、评测集与本地产物
docs/               版本记录、验收报告、演示和面试材料
bad_cases/          bad case 记录
scripts/            demo 启停脚本
prompts/            版本推进 prompt
```

## 核心接口

```text
GET  /healthz              liveness（进程存活）       公开
GET  /readyz               readiness（依赖就绪）      公开
GET  /health               legacy 健康检查            公开
GET  /metrics              Prometheus metrics         公开（需 METRICS_ENABLED=true）
GET  /api/v1/system/status                           viewer
GET  /api/v1/acceptance/overview                      viewer
POST /api/v1/documents/ingest                         operator
POST /api/v1/documents/upload                         operator
POST /api/v1/chat                                     viewer
POST /api/v1/chat/session                             viewer
POST /api/v1/chat/stream                              viewer
POST /api/v1/tickets/start                            operator
GET  /api/v1/tickets                                   viewer
POST /api/v1/tickets/{ticket_id}/resume               operator
POST /api/v1/tickets/{ticket_id}/close                operator
POST /api/v1/evaluations/run                          admin
POST /api/v1/jobs/ingest                              operator
POST /api/v1/jobs/evaluations                         admin
POST /api/v1/jobs/{job_id}/cancel                     operator+
GET  /api/v1/jobs/{job_id}                            viewer
GET  /api/v1/jobs                                     viewer
GET  /api/v1/admin/audit/events                       admin
```

## 认证

默认 `AUTH_ENABLED=false`，所有接口无需认证。

开启后通过 `X-API-Key` 请求头认证，角色层级 viewer < operator < admin：

```bash
curl -X POST -H "X-API-Key: your-operator-key" -H "Content-Type: application/json" -d "{}" http://localhost:8000/api/v1/documents/ingest
```

健康检查端点（/healthz、/readyz、/health）始终公开，不要求 API Key。

## 证据索引

文本 LLM / Provider：

- [A-v1.4 Provider 稳定性收口与默认模型决策](docs/A-v1.4_真实LLM_Provider稳定性收口与默认模型决策.md)
- [A-v1.4 Provider 验收报告 2026-05-19](docs/A-v1.4_provider_acceptance_report_2026-05-19.json)
- [A-v1.4 DeepSeek grounded 预检](docs/A-v1.4_real_llm_grounding_preflight_deepseek_2026-05-19.json)
- [A-v2.2 MiMo Provider 重新验收](docs/A-v2.2-mimo-provider-reacceptance.md)
- [A-v2.2 Provider 验收报告 2026-05-23](docs/A-v2.2_provider_acceptance_report_2026-05-23.json)
- [A-v2.4 Provider 对比报告复盘](docs/A-v2.4-provider-comparison-review.md)
- [A-v2.4 Provider 对比 JSON](docs/A-v2.4_provider_comparison_report_2026-05-23.json)

多模态：

- [A-v1.5 真实多模态全链路开启与验收收口](docs/A-v1.5_真实多模态全链路开启与验收收口.md)
- [A-v1.5 多模态验收报告 2026-05-20](docs/A-v1.5_multimodal_acceptance_report_2026-05-20.json)
- [A-v1.5 PaddleOCR 最终探针](docs/A-v1.5_paddleocr_linux_final_probe_2026-05-20.json)
- [A-v1.5 bad cases](docs/A-v1.5_bad_cases.md)
- [A-v2.3 PaddleOCR 兼容性专项复盘](docs/A-v2.3-paddleocr-compatibility-review.md)
- [A-v2.3 PaddleOCR 兼容性报告](docs/A-v2.3_paddleocr_compatibility_report_2026-05-23.json)

演示中心：

- [A-v1.6 验收中心与演示产品化](docs/A-v1.6_验收中心与演示产品化.md)
- [A-v2.0 前端验收中心与演示产品化](docs/A-v2.0_前端验收中心与演示产品化.md)
- [A-v2.0 前端 live preflight public chain](docs/A-v2.0_frontend_live_preflight_publicchain_2026-05-22.json)

评测与 bad case：

- [A-real-data RAGAS 报告](docs/A-real-data_ragas_report.json)
- [A-real-data 回归报告](docs/A-real-data_regression_report.json)
- [A-real-data 对抗报告](docs/A-real-data_adversarial_report.json)
- [A-real-data bad cases](docs/A-real-data_bad_cases.md)
- [A-v2.9 评测质量提升复盘](docs/A-v2.9-evaluation-quality-review.md)
- [A-v2.9 bad cases](docs/A-v2.9_bad_cases.md)

A-v2.1 交付文档：

- [最终交付索引](docs/final_delivery_index.md)
- [Demo 启动指南](docs/demo_guide.md)
- [标准演示脚本](docs/demo_script.md)
- [五分钟演示路线](docs/five_min_demo_route.md)
- [演示素材清单](docs/demo_assets_checklist.md)
- [公开交付 Checklist](docs/public_delivery_checklist.md)
- [面试讲法索引](docs/interview_guide.md)
- [面试材料压缩包](docs/interview_pitch_pack.md)
- [A-v2.1 演示与交付收口复盘](docs/A-v2.1-demo-delivery-review.md)
- [A-v2.5 演示素材补强复盘](docs/A-v2.5-demo-assets-review.md)
- [A-v2.6 公开交付检查复盘](docs/A-v2.6-public-delivery-review.md)
- [A-v2.7 面试材料压缩版复盘](docs/A-v2.7-interview-compression-review.md)
- [A-v2.8 作品集视觉补图复盘](docs/A-v2.8-portfolio-visual-assets-review.md)
- [A-v2.9 评测质量提升与样本扩容复盘](docs/A-v2.9-evaluation-quality-review.md)
- [A-v3.0 最终公开发布复核](docs/A-v3.0-public-release-verification.md)
- [A-v3.1 公开展示与面试讲法收口](docs/A-v3.1-public-readability-review.md)
- [A-v3.2 远端 CI 与公开展示复核](docs/A-v3.2-remote-ci-display-review.md)
- [A-v3.3 轻量作品集入口增强](docs/A-v3.3-portfolio-entry-review.md)
- [A-v3.4 简历投递材料收口](docs/A-v3.4-resume-delivery-pack.md)
- [A-v3.5 远端最终巡检](docs/A-v3.5-final-remote-audit.md)
- [A-v3.6 公开交付 Release Notes](docs/A-v3.6-public-release-notes.md)

截图资产：

- [A-v2.5 demo 首页截图](docs/assets/a-v2.5/01-demo-home.png)
- [Provider 状态截图](docs/assets/a-v2.5/02-provider-status.png)
- [多模态状态截图](docs/assets/a-v2.5/03-multimodal-status.png)
- [Evaluation Trace 截图](docs/assets/a-v2.5/04-evaluation-trace.png)
- [Trace JSON 截图](docs/assets/a-v2.5/05-trace-json.png)
- [Provider 对比摘要截图](docs/assets/a-v2.5/06-provider-comparison-report.png)

## 面试讲法

一句话版本：

> 这个项目把设备售后诊断场景做成了可检索、可引用、可评测、可追踪、可演示的 RAG 闭环，而不是只包装一个聊天接口。

重点讲：

- grounded 回答：真实 LLM 只有通过上下文校验才接管最终回答。
- provider 验收：把认证失败、配置缺失、grounded rejection 分开记录。
- 多模态验收：明确 Vision / MinerU / PaddleOCR 的真实状态和阻塞层。
- bad case 闭环：低分 case 能追到 trace，能解释问题在召回、上下文还是答案决策。
- 演示中心：不是静态说明页，而是读取真实验收报告聚合展示。

完整问答见：[docs/interview_guide.md](docs/interview_guide.md)。

临场压缩讲法见：[docs/interview_pitch_pack.md](docs/interview_pitch_pack.md)。

## 下一步规划

推荐顺序：

1. **可选 GitHub Release 页面**：如果需要更正式的发布页，可基于 `docs/A-v3.6-public-release-notes.md` 在 GitHub 创建 Release。
2. **可选 OCR spike**：单独开 Docker clean runtime matrix，再决定是否重新启用 PaddleOCR。
