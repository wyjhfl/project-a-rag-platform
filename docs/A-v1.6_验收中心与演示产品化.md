# A-v1.6 验收中心与演示产品化

## 1. 本版本解决的业务问题

A-v1.4 和 A-v1.5 已经分别拿到了真实文本主链与真实多模态链路的证据，但这些证据分散在 `docs/*.json` 和 `docs/*.md` 里，演示时仍要手动翻文档。

A-v1.6 的目标不是再加新能力，而是把已经完成的能力做成前端可讲、可看、可截图的验收中心。

## 2. 核心技术点

- 证据聚合接口
  - 不重新计算 provider、multimodal、evaluation 结果，而是直接读取现有验收报告。
  - 价值是把“版本证据”转成稳定的 API 数据结构。
- 前端验收面板
  - 把文本主链、多模态、评测、bad case 拆成四块卡片。
  - 每块同时展示状态、摘要、关键指标、证据路径。
- 展示层与业务链解耦
  - A-v1.6 不改 RAG 主链，不碰多模态执行逻辑，只做读取与展示。
  - 这样风险最小，也更符合“产品化收口”定位。

## 3. 版本技术设计

### 本轮目标

- 新增 `/api/v1/acceptance/overview`
- 前端新增“验收中心”页签
- 修复原有 `App.vue` 中文乱码，统一成可演示界面

### 本轮不做什么

- 不新增新的 RAG 能力
- 不重跑 provider / multimodal 验收脚本
- 不在这一版做图表系统或 trace 深度可视化

### 涉及文件

- `backend/app/models.py`
- `backend/app/main.py`
- `backend/tests/test_acceptance_overview_api.py`
- `frontend/src/api.ts`
- `frontend/src/App.vue`
- `frontend/src/styles.css`

## 4. 最小实现

### 后端

- 新增 `AcceptanceOverviewResponse / AcceptancePanel / AcceptanceEvidenceItem`
- 新增 `/api/v1/acceptance/overview`
- 聚合以下证据：
  - `docs/A-v1.4_provider_acceptance_report_2026-05-19.json`
  - `docs/A-v1.5_multimodal_acceptance_report_2026-05-20.json`
  - `docs/A-real-data_regression_report.json`
  - `docs/A-real-data_ragas_report.json`
  - `docs/A-real-data_adversarial_report.json`
  - `docs/A-real-data_bad_cases.md`
  - `docs/A-v1.5_bad_cases.md`

### 前端

- 重写 `App.vue`
- 新增“验收中心”首页
- 保留系统状态、资料管理、问答、多轮、工单、评测、bad case 页签
- 统一修复中文乱码与页面层级

## 5. 当前代码链路如何运行

1. 前端加载时调用：
   - `/api/v1/system/status`
   - `/api/v1/tickets`
   - `/api/v1/acceptance/overview`
2. 后端读取最新验收报告和 bad case 文档
3. 聚合成四个面板：
   - 真实 LLM 主链
   - 真实多模态能力
   - 评测与回归
   - Bad Case 与边界
4. 前端按卡片形式展示状态、指标和证据路径

## 6. 验证

已完成：

- `pytest backend/tests/test_acceptance_overview_api.py -q`
- `python -m compileall backend/app/main.py backend/app/models.py`
- `cd frontend && npm run build`

结果：

- 后端测试 `1 passed`
- Python 编译通过
- 前端构建通过

## 7. 面试怎么讲

可以这样讲：

“我没有把项目停留在脚本和文档层，而是做了一个前端验收中心，把真实 LLM 默认主链、真实多模态验收状态、评测结果和 bad case 统一成一个界面。这样演示时不需要翻文档，能直接说明哪些链路已转绿，哪些链路为什么没转绿，以及证据文件在哪里。” 

## 8. 下一版本如何衔接

下一步最自然的是继续做 `A-v2.0` 风格的展示增强，而不是回头再堆底层能力：

- provider 状态面板再图表化
- trace 可视化入口
- bad case 展示页细化
- evaluation 报告图形化

当前 A-v1.6 已经把这些增强所需的数据入口准备好了。
