# A-v2.5 五分钟演示路线

## 0:00 - 0:30 项目定位

一句话：

> 这是一个企业设备售后诊断 RAG 平台，从故障描述出发，完成检索、引用、grounded 回答、评测、trace 和工单闭环。

必须点到：

- 不是普通聊天 demo。
- 面向设备售后诊断。
- 重点是可验证业务闭环。

## 0:30 - 1:00 本地 demo 画像

展示：

- `.env.demo.example`
- `scripts/start_demo_stack.ps1`

讲法：

> 公开演示固定为 sqlite + chroma + deepseek-chat，企业增强依赖不放进默认路径，避免演示被外部组件阻塞。

## 1:00 - 2:00 前端验收中心

展示：

- 前端首页
- Provider 状态
- 多模态状态
- evaluation / bad case / trace

讲法：

> 这个页面不是宣传页，而是读取真实验收报告，把 provider、多模态、评测和坏例子集中展示。

## 2:00 - 3:00 Provider 主线

展示：

- `docs/A-v2.2_provider_acceptance_report_2026-05-23.json`
- `docs/A-v2.4_provider_comparison_report_2026-05-23.json`

讲法：

> DeepSeek 是当前默认公开 demo 主链；MiMo v2.5 已经从认证阻塞推进到可比较候选；MiMo v2.5 Pro 因延迟和 fallback 暂不进默认路径。

## 3:00 - 4:00 多模态边界

展示：

- `docs/A-v1.5_multimodal_acceptance_report_2026-05-20.json`
- `docs/A-v2.3_paddleocr_compatibility_report_2026-05-23.json`

讲法：

> Vision LLM 和 MinerU Linux sliced 已转绿；PaddleOCR 当前是 runtime compatibility boundary，不包装成已完成能力。

## 4:00 - 4:40 Evaluation / Bad Case / Trace

展示：

- evaluation 面板
- trace 详情
- bad case 卡片

讲法：

> bad case 不是失败记录而已，它和 trace 一起用于定位问题发生在召回、上下文、rerank 还是答案决策。

## 4:40 - 5:00 收束

结尾：

> 这个项目最重要的是每条能力都有验收状态、证据文件和边界说明。它展示的是把 RAG 做成可排查、可评测、可演示的工程系统。

下一步：

- 公开交付检查。
- 截图和短录屏。
- 敏感信息排查。
- 公开仓库导出。
