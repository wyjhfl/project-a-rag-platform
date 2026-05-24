# A-v2.6 公开交付 Checklist

## 目标

在项目公开展示或导出公开仓库前，确认演示、证据、敏感信息和文档入口都已经收口。

## 必查项

### 0. 最终入口

- README 能作为第一入口。
- `docs/final_delivery_index.md` 能串起 demo、证据、截图和面试材料。
- `docs/A-v2.6-public-delivery-review.md` 记录本轮交付检查结论。

### 1. 敏感信息

- `.env` 不提交。
- `.env.demo.example` 不包含真实 key。
- 文档中不出现真实 API key。
- JSON 报告中不出现真实 API key。
- 截图中不出现真实 API key。

### 2. Demo 启动

必须通过：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_demo_stack.ps1 -StopExisting
```

必须可访问：

```text
http://127.0.0.1:18082/health
http://127.0.0.1:18082/api/v1/system/status
http://127.0.0.1:18082/api/v1/acceptance/overview
http://127.0.0.1:4175/
http://127.0.0.1:4175/api/v1/acceptance/overview
```

### 3. README

README 必须说明：

- 项目定位。
- 当前推荐 demo 画像。
- 快速启动。
- 当前已转绿能力。
- 当前边界。
- 证据索引。
- 下一步规划。

### 4. 证据链

必须存在：

- `docs/A-v2.2_provider_acceptance_report_2026-05-23.json`
- `docs/A-v2.3_paddleocr_compatibility_report_2026-05-23.json`
- `docs/A-v2.4_provider_comparison_report_2026-05-23.json`
- `docs/A-real-data_ragas_report.json`
- `docs/A-real-data_bad_cases.md`

### 5. 演示材料

必须存在：

- `docs/demo_guide.md`
- `docs/demo_script.md`
- `docs/five_min_demo_route.md`
- `docs/demo_assets_checklist.md`
- `docs/interview_guide.md`

### 6. 边界说明

必须能讲清：

- 为什么 DeepSeek 是默认 demo 主链。
- MiMo 当前是什么状态。
- PaddleOCR 为什么不进入默认路径。
- Vision LLM 和 MinerU Linux sliced 为什么可以讲。
- bad case 和 trace 如何闭环。

## 当前公开口径

```text
默认 demo：sqlite + chroma + deepseek-chat
候选 provider：mimo-v2.5
多模态可讲：Vision LLM + MinerU Linux sliced
OCR 边界：PaddleOCR runtime compatibility boundary
```

## 交付结论

满足本 checklist 后，项目可以作为作品集仓库继续整理公开导出。

当前 A-v2.6 状态：

- 最终交付索引已补齐。
- 公开导出脚本已补入 A-v2.2 到 A-v2.6 核心材料。
- 公开 demo 五个入口已在本轮回归中复核通过。
- 敏感信息扫描未发现真实 API key。
- 服务已停止，`18082` 和 `4175` 端口已释放。
