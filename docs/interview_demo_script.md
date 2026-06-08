# Interview Demo Script - Project A

## 目标

用 5-10 分钟把 Project A 讲成一个完整 AI 工程项目，而不是“调了一个大模型接口”。

## 0. 准备

推荐先运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_full_e2e_demo.ps1 `
  -PythonExe "D:\path\to\Python312\python.exe" `
  -NpmCmd "D:\path\to\nodejs\npm.cmd"
```

如果只演示 UI，可打开：

```text
http://127.0.0.1:4173
```

## 1. 30 秒开场

“这是一个企业设备售后诊断 RAG 平台。输入设备型号、故障码或现场现象后，系统会检索企业资料并生成带引用的排障建议。如果资料不足或操作高风险，会拒答或升级人工工单。工程上我做了异步任务、审计日志、metrics、OpenAPI 类型同步、E2E 和生产验收脚本。”

## 2. Acceptance 页：先讲项目价值

展示点：

- 面试展示入口卡片
- 技术亮点
- Demo 路线
- 验收面板

讲法：

“我把面试时需要讲的业务价值、技术亮点和验收证据放在默认页，面试官打开项目后不用翻代码就能理解这个系统解决什么问题。”

## 3. System Status：讲可运维性

展示点：

- `/healthz`
- `/readyz`
- release link
- `/metrics` summary
- Request ID 错误卡片

讲法：

“生产系统不能只有功能，还要能排障。所以我做了 liveness/readiness、统一错误格式、Request ID 和 Prometheus metrics。前端直接展示这些信号。”

## 4. Quality：讲 RAG 质量与工程取舍

展示点：

- regression 通过率
- context_precision / faithfulness / context_recall
- Bad Case 边界
- 低分 Trace 复盘
- Demo 成本、外部队列、Grafana/OTel 等取舍

讲法：

“RAG 项目不能只演示一条问答。我单独做了质量洞察页，把评测指标、bad case、trace 和工程取舍集中展示。这样面试官追问‘怎么证明效果’和‘怎么生产化’时，可以直接从 UI 讲到测试和架构。”

## 5. Documents + Jobs：讲异步化

展示点：

- 资料入库按钮
- Job 列表
- 状态、取消、重试、错误摘要

讲法：

“文档入库和评测可能很慢，所以我把它们放到 Job 模型里。Job 有 PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED 状态，worker 通过 claim 避免重复执行，并支持 cancel、retry、timeout 和 heartbeat。”

## 6. Chat：讲 grounded answer

展示点：

- RAG 问答
- 引用证据
- 资料不足时的拒答边界

讲法：

“我不希望系统编答案，所以回答必须绑定检索上下文和引用。资料不足时应该拒答或升级工单，这比强行回答更符合企业售后场景。”

## 7. Tickets：讲人工闭环

展示点：

- 工单启动
- 人工确认
- 关闭工单

讲法：

“RAG 不是替代所有人工。高风险或资料不足时升级人工，这样系统边界更安全，也更接近真实业务。”

## 8. Evaluations + Audit：讲质量闭环

展示点：

- 异步评测
- 审计日志
- request_id

讲法：

“我把评测和审计做成产品的一部分。评测回答‘效果如何’，审计回答‘发生了什么、谁触发的、怎么排查’。”

## 9. 收束

最后打开 GitHub Actions 或本地验收输出：

“这个项目的交付不是手工点一点，而是有最终生产验收脚本，覆盖后端测试、ruff、前端构建、OpenAPI drift、secret scan、Docker Compose、PostgreSQL/Redis smoke、worker stress 和 Full E2E。”

## 常见追问速答

- **为什么用 RAG？** 企业售后知识更新频繁，需要 grounded answer 和引用证据。
- **怎么防幻觉？** 检索上下文、引用证据、拒答边界、评测和 bad case 复盘。
- **怎么扩展到生产？** PostgreSQL/Redis/Milvus compose、worker、metrics、readyz、final acceptance。
- **最大不足？** Grafana/OTel、Alembic、外部队列和更多真实样本仍可继续增强。
