# A-v2.0 前端验收中心与演示产品化

## 1. 本版本解决的业务问题

A-v1.6 已经把验收结果接进前端，但它更像“把 JSON 放到了页面上”，还不够适合演示。

A-v2.0 的目标是把这套页面升级成真正的演示中心：

- 能看出主链是否稳定
- 能看出多模态哪些链路已转绿
- 能看出评测分数和风险集中在哪
- 能直接展示 bad case，而不是只给文档路径

## 2. 核心技术点

- 单接口承载展示层数据
  - 继续沿用 `/api/v1/acceptance/overview`
  - 不重复计算验收，只扩充可视化所需结构
- 面板明细化
  - 每块面板除了 summary，还要有 `breakdown`
  - 让演示时可以讲“哪个 provider / 哪个组件为什么是这个状态”
- 图表轻量化
  - 不引入新图表库
  - 用前端原生布局 + 进度条做最小可运行可视化
- bad case 卡片化
  - 从评测报告和 Markdown 里抽重点样例
  - 让“失败模式”可以直接在前端被讲出来

## 3. 本轮实现

### 后端

- `backend/app/main.py`
  - 版本号升级为 `v2.0`
  - 扩展 `/api/v1/acceptance/overview`
  - 新增：
    - `breakdown`
    - `chart`
    - `highlights`
- `backend/app/models.py`
  - 新增：
    - `AcceptanceBreakdownItem`
    - `AcceptanceChartBar`
    - `AcceptanceHighlightItem`

### 前端

- `frontend/src/App.vue`
  - 将验收中心升级为真正的演示中心首页
  - 增加：
    - 顶部总览指标
    - 面板图形化指标
    - provider / multimodal 明细块
    - 低分样例与 bad case 卡片
    - 低分 case 的 trace 时间线入口
    - 低分 case 的 trace 筛选与原始 JSON 查看
- `frontend/src/styles.css`
  - 增强页面层次与展示节奏
  - 保持移动端可读
- `frontend/src/api.ts`
  - 补齐新响应类型

## 4. 当前代码链路如何运行

1. 前端进入“演示中心”
2. 调用 `/api/v1/acceptance/overview`
3. 后端读取：
   - `A-v1.4 provider` 报告
   - `A-v1.5 multimodal` 报告
   - `A-real-data` 评测报告
   - `A-v1.2_ragas_report.json`
   - `A-real-data_bad_cases.md`
   - `A-v1.5_bad_cases.md`
4. 聚合成四个面板：
   - 真实 LLM 主链
   - 真实多模态能力
   - 评测与回归
   - Bad Case 与边界
5. 前端把它展示成：
   - 概览指标
   - 分数条
   - 组件明细
   - 重点样例
   - trace 时间线
   - 证据文件

## 5. 验证

已完成：

- `pytest backend/tests/test_acceptance_overview_api.py backend/tests/test_api.py backend/tests/test_enterprise_api.py -q`
- `python -m compileall backend/app/main.py backend/app/models.py`
- `cd frontend && npm run build`

结果：

- `9 passed`
- Python 编译通过
- 前端构建通过

## 6. 当前结论

A-v2.0 现在已经不是“把验收结果放到前端”，而是：

- 可以直接讲默认文本主链候选是谁
- 可以直接讲多模态哪些链路已绿
- 可以直接讲低分样例和 bad case
- 可以直接讲某个低分 case 经过了哪些 trace 节点
- 可以直接展开 trace 的关键输入输出，必要时查看原始 trace JSON
- 可以直接指向证据文件

## 7. 面试怎么讲

“我把真实验收结果做成了一个前端演示中心。它不是静态说明页，而是直接读取真实 provider、多模态和评测报告，展示哪些链路已转绿、哪些链路阻塞在哪、哪些 bad case 还没被解决。这样面试时我不需要翻文档，可以直接按状态板讲整条工程闭环。”

## 8. 下一步如何衔接

最自然的下一步不是继续堆页面，而是继续补两类高价值增强：

- trace 可视化入口
- evaluation 图表和筛选交互

当前 A-v2.0 已经把这两步需要的数据骨架准备好了。

## 9. 2026-05-22 实机联调补充

这轮不再只停留在接口测试和前端构建，而是做了真实本地联调。

### 现象

- 当前仓库 `.env` 默认面向企业增强开发：
  - `STORAGE_BACKEND=postgres`
  - `CACHE_ENABLED=true`
  - `GRAPH_RETRIEVAL_ENABLED=true`
- 这会导致公开演示时直接跑 `preflight_frontend_full_test.py` 被 PostgreSQL 初始化阻塞。

### 处理

- 补强 `backend/scripts/preflight_frontend_full_test.py`
- 新增 `--profile public_chain`
- 该画像会强制切回：
  - `STORAGE_BACKEND=sqlite`
  - `VECTOR_BACKEND=chroma`
  - `CACHE_ENABLED=false`
  - `GRAPH_RETRIEVAL_ENABLED=false`
  - `LLM_PROVIDER=deepseek`
  - `LLM_MODEL=deepseek-chat`

### 实测结果

- 后端以公开主链画像启动后：
  - `GET /health` 返回 `200`
  - `GET /api/v1/system/status` 返回 `200`
  - `GET /api/v1/acceptance/overview` 返回 `200`
- 前端以 `VITE_API_BASE_URL=http://127.0.0.1:18082` 启动后：
  - 首页返回 `200`
  - 代理到 `/api/v1/acceptance/overview` 返回 `200`

### 结论

A-v2.0 现在不仅是“页面做完、接口做完、构建通过”，而且已经完成一轮真实本地演示联调。当前最稳定的演示口径就是：

1. 后端使用 `public_chain` 覆盖画像
2. 前端单独指定 `VITE_API_BASE_URL`
3. 直接演示验收中心、trace、bad case 和多模态状态板

## 10. 2026-05-22 演示启动资产补齐

为了避免 A-v2.0 仍然依赖“记住一组临时命令”，补了三项可交付资产：

- `.env.demo.example`
  - 演示画像模板
  - 固化 `sqlite + chroma + deepseek-chat`
- `scripts/start_demo_stack.ps1`
  - 自动加载 `.env` 与 `.env.demo`
  - 自动把 `DEEPSEEK_API_KEY` 映射到 `LLM_API_KEY`
  - 自动启动 FastAPI 与 Vite
  - 自动等待页面和 API ready
- `scripts/stop_demo_stack.ps1`
  - 自动清理演示进程

这一步之后，A-v2.0 的交付形态已经从：
- 页面可展示
- 接口可聚合
- trace 可讲解

推进到：
- 本地可复现启动
- 演示画像可复用
- 启停链路可交接
