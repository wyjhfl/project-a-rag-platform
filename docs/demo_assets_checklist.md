# A-v2.5 演示素材清单

## 目标

把当前“可运行项目”整理成“可展示作品集素材”。

素材分为四类：

- 截图
- 讲解路线
- 证据文件索引
- 公开交付 checklist

## 已有截图资产

已有旧版截图：

```text
docs/assets/a-v1.1/01-system-status.png
docs/assets/a-v1.1/02-chat-a100-e17.png
docs/assets/a-v1.1/03-ticket-hitl.png
docs/assets/a-v1.1/04-evaluation-center.png
docs/assets/a-v1.1/05-swagger-docs.png
```

这些截图可作为历史版本参考，但 A-v2.5 对外展示应优先使用新版演示中心截图。

## A-v2.8 推荐截图

截图目录：

```text
docs/assets/a-v2.5/
```

推荐文件：

- `01-demo-home.png`：前端演示中心首页。
- `02-provider-status.png`：Provider 状态区，展示 DeepSeek / MiMo。
- `03-multimodal-status.png`：多模态状态区，展示 Vision / MinerU / PaddleOCR 边界。
- `04-evaluation-trace.png`：evaluation + trace 时间线。
- `05-trace-json.png`：原始 trace JSON 弹层。
- `06-provider-comparison-report.png`：A-v2.4 provider 对比 JSON 或文档摘要。

## 截图验收标准

每张截图应满足：

- 不显示真实 API key。
- 地址栏可显示 localhost，但不能暴露本地敏感路径。
- 页面文字无遮挡。
- 能看出项目是 RAG 验收 / 演示中心，而不是普通后台页面。
- 文件名按演示顺序排序。

## 当前已生成

- `docs/assets/a-v2.5/01-demo-home.png`
- `docs/assets/a-v2.5/02-provider-status.png`
- `docs/assets/a-v2.5/03-multimodal-status.png`
- `docs/assets/a-v2.5/04-evaluation-trace.png`
- `docs/assets/a-v2.5/05-trace-json.png`
- `docs/assets/a-v2.5/06-provider-comparison-report.png`

## 讲解材料

- `docs/demo_script.md`
- `docs/five_min_demo_route.md`
- `docs/interview_guide.md`

## 证据材料

Provider：

- `docs/A-v2.2_provider_acceptance_report_2026-05-23.json`
- `docs/A-v2.4_provider_comparison_report_2026-05-23.json`

多模态：

- `docs/A-v1.5_multimodal_acceptance_report_2026-05-20.json`
- `docs/A-v2.3_paddleocr_compatibility_report_2026-05-23.json`

演示交付：

- `docs/A-v2.1-demo-delivery-review.md`
- `docs/A-v2.5-demo-assets-review.md`
- `docs/A-v2.8-portfolio-visual-assets-review.md`
