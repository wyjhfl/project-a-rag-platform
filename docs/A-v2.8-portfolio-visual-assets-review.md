# A-v2.8 作品集视觉补图复盘

## 本轮目标

A-v2.8 不新增业务能力，目标是补齐作品集截图，让项目从“能讲清楚”推进到“打开就能看懂”。

本轮重点：

- Provider 状态截图。
- 多模态状态截图。
- evaluation + trace 截图。
- trace JSON 弹层截图。
- provider comparison 摘要截图。

## 本轮边界

不做：

- 不改 RAG 主链。
- 不改前端交互。
- 不重新跑 provider 或多模态验收。
- 不生成新评测数据。

只做：

- 基于现有 demo 和真实报告截图。
- 更新截图清单。
- 更新交付索引。
- 做最小回归验证。

## 核心产物

截图目录：

```text
docs/assets/a-v2.5/
```

已生成：

- `01-demo-home.png`
- `02-provider-status.png`
- `03-multimodal-status.png`
- `04-evaluation-trace.png`
- `05-trace-json.png`
- `06-provider-comparison-report.png`

更新：

- `docs/assets/a-v2.5/README.md`
- `docs/demo_assets_checklist.md`
- `README.md`
- `docs/final_delivery_index.md`
- `docs/dev_log.md`
- `docs/debug_log.md`
- `backend/scripts/create_public_release_repo.py`

新增：

- `docs/A-v2.8-portfolio-visual-assets-review.md`
- `docs/A-v2.8_bad_cases.md`

## 截图来源

前五张来自本地 demo：

```text
http://127.0.0.1:4175/
```

第六张来自 A-v2.4 真实 provider comparison 结果摘要：

```text
docs/A-v2.4_provider_comparison_report_2026-05-23.json
```

## 验证结果

demo 入口回归：

```text
GET http://127.0.0.1:18082/health -> 200
GET http://127.0.0.1:18082/api/v1/system/status -> 200
GET http://127.0.0.1:18082/api/v1/acceptance/overview -> 200
GET http://127.0.0.1:4175/ -> 200
GET http://127.0.0.1:4175/api/v1/acceptance/overview -> 200
```

截图检查：

```text
6 张截图均已生成并人工查看。
05-trace-json.png 已重截为弹层本体，避免遮罩影响可读性。
06-provider-comparison-report.png 已重制为英文摘要图，避免 PowerShell inline Node 编码污染中文。
```

服务状态：

```text
PORT 18082 released
PORT 4175 released
```

## 面试讲法

> A-v2.8 我补的是作品集视觉证据。之前项目已经能讲、能跑、能验收，这一轮把 provider、多模态、evaluation、trace JSON 和 provider 对比做成截图素材，面试或作品集展示时不用只靠口头解释。

## 下一步

推荐进入 A-v2.9 最终公开导出复核：

- 重新导出 public release。
- 从导出包按 README 从零启动。
- 复核截图、面试材料和证据索引是否都在公开包中。
