# A-v2.6 公开交付检查复盘

## 本轮目标

A-v2.6 不新增 RAG 能力，目标是把公开交付入口最终收口。

本轮重点：

- 新增最终交付索引。
- 更新 README 中过时的下一步和演示顺序。
- 同步面试讲法里的 MiMo / PaddleOCR 最新状态。
- 复核公开导出脚本，补入 A-v2.2 到 A-v2.6 核心材料。
- 做一次公开 demo 回归。
- 做敏感信息扫描。

## 本轮边界

不做：

- 不新增 provider。
- 不重新调参 OCR。
- 不改 RAG 检索和生成主链。
- 不做新前端页面。

只做：

- 交付材料索引。
- 公开导出清单修正。
- 文档口径同步。
- 最小回归验证。

## 核心产物

新增：

- `docs/final_delivery_index.md`
- `docs/A-v2.6-public-delivery-review.md`
- `docs/A-v2.6_bad_cases.md`

更新：

- `README.md`
- `docs/interview_guide.md`
- `docs/public_delivery_checklist.md`
- `backend/scripts/create_public_release_repo.py`
- `docs/dev_log.md`
- `docs/debug_log.md`

## 当前交付链路

```text
README
-> demo_guide
-> start_demo_stack.ps1
-> FastAPI / Vue 验收中心
-> final_delivery_index
-> demo_script / five_min_demo_route / interview_guide
-> A-v2.2 / A-v2.3 / A-v2.4 / A-v2.5 / A-v2.6 证据
```

## 公开口径

默认 demo：

```text
sqlite + chroma + deepseek-chat
```

候选 provider：

```text
mimo-v2.5
```

多模态可讲：

```text
Vision LLM + MinerU Linux sliced
```

明确边界：

```text
PaddleOCR = runtime compatibility boundary
```

## 验收标准

必须满足：

- README 能作为第一入口。
- 最终交付索引能串起所有关键材料。
- 公开导出脚本不复制 `.env`。
- demo 五个 HTTP 入口可访问。
- 敏感信息扫描不命中文档、脚本和 demo example 中的真实 key。
- 未转绿能力以边界表达，不包装成成功能力。

## 验证结果

公开导出 dry run：

```text
python backend/scripts/create_public_release_repo.py --target tmp/public-release-check --force
public_release_repo=tmp/public-release-check
```

导出包已确认包含：

- `docs/final_delivery_index.md`
- `docs/A-v2.6-public-delivery-review.md`
- `docs/A-v2.2_provider_acceptance_report_2026-05-23.json`
- `docs/A-v2.3_paddleocr_compatibility_report_2026-05-23.json`
- `docs/A-v2.4_provider_comparison_report_2026-05-23.json`
- `docs/assets/a-v2.5/01-demo-home.png`
- `scripts/start_demo_stack.ps1`
- `.env.demo.example`

敏感信息扫描：

```text
未发现真实 API key。
命中项仅为脚本中的变量传递和 demo guide 中的占位说明。
```

自动化验证：

```text
python -m compileall backend\scripts\create_public_release_repo.py
passed

python -m pytest backend\tests\test_acceptance_overview_api.py backend\tests\test_av24_provider_comparison.py -q
3 passed
```

公开 demo 回归：

```text
GET http://127.0.0.1:18082/health -> 200
GET http://127.0.0.1:18082/api/v1/system/status -> 200
GET http://127.0.0.1:18082/api/v1/acceptance/overview -> 200
GET http://127.0.0.1:4175/ -> 200
GET http://127.0.0.1:4175/api/v1/acceptance/overview -> 200
```

服务状态：

```text
PORT 18082 released
PORT 4175 released
```

## 面试讲法

> A-v2.6 我做的是交付收口，不是继续堆功能。项目已经具备文本主链、多模态边界、provider 对比、evaluation、bad case 和 trace 的真实证据，所以这一轮重点是把它整理成一个面试官能快速理解、我也能稳定演示的作品包。

## 下一步

推荐进入 A-v2.7 面试材料压缩版：

- 2 分钟自我介绍版。
- 5 分钟项目演示版。
- 15 分钟深挖技术版。
- 高频追问回答。
