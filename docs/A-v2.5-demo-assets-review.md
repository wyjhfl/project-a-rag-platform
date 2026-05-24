# A-v2.5 演示素材补强复盘

## 本轮目标

A-v2.5 不新增 RAG 能力，目标是把当前项目整理成可展示作品集材料。

本轮重点：

- 更新演示脚本到 A-v2.4 最新状态。
- 固化 5 分钟演示路线。
- 固化截图清单。
- 固化公开交付 checklist。
- 补充当前 demo 首页截图。
- 同步前端验收中心证据源，避免截图仍展示旧结论。

## 本轮边界

不做：

- 不改 RAG 主链。
- 不改前端交互。
- 不新增 provider。
- 不重新跑大规模评测。

只做：

- 演示材料整理。
- 截图入口整理。
- demo 可用性验证。
- 公开交付 checklist。
- 验收中心证据源同步。

## 本轮产物

新增：

- `docs/five_min_demo_route.md`
- `docs/demo_assets_checklist.md`
- `docs/public_delivery_checklist.md`
- `docs/A-v2.5-demo-assets-review.md`
- `docs/assets/a-v2.5/README.md`
- `docs/assets/a-v2.5/01-demo-home.png`

更新：

- `docs/demo_script.md`
- `README.md`
- `docs/dev_log.md`
- `docs/debug_log.md`
- `backend/app/main.py`

## 验收中心同步

截图检查时发现演示中心仍优先读取 A-v1.4 provider 报告，导致页面里 MiMo 仍显示旧的 `auth_invalid` 状态。

本轮已修正：

- Provider 面板优先读取 `A-v2.2_provider_acceptance_report*.json`。
- Provider 默认候选仍显示 `deepseek_chat`。
- MiMo v2.5 显示为候选对照。
- 多模态面板补充 A-v2.3 PaddleOCR compatibility boundary 证据。

## 当前演示口径

默认 demo：

```text
sqlite + chroma + deepseek-chat
```

候选 provider：

```text
mimo-v2.5
```

多模态：

```text
Vision LLM + MinerU Linux sliced
```

明确边界：

```text
PaddleOCR = runtime compatibility boundary
```

## 验证

HTTP 入口：

```text
GET http://127.0.0.1:18082/health -> 200
GET http://127.0.0.1:18082/api/v1/system/status -> 200
GET http://127.0.0.1:18082/api/v1/acceptance/overview -> 200
GET http://127.0.0.1:4175/ -> 200
GET http://127.0.0.1:4175/api/v1/acceptance/overview -> 200
```

截图：

```text
docs/assets/a-v2.5/01-demo-home.png
```

测试：

```text
python -m pytest backend/tests/test_acceptance_overview_api.py -q
1 passed

python -m compileall backend\app\main.py
passed
```

## 面试讲法

> A-v2.5 我没有继续堆功能，而是把项目整理成可展示材料。现在 README、五分钟路线、完整演示脚本、截图清单、公开交付 checklist 和真实验收报告是互相对齐的。面试时可以直接按这条路线讲完整工程闭环，不需要临场翻散乱文档。

## 下一步

推荐进入 A-v2.6 公开交付检查：

- 敏感信息扫描。
- 公开仓库导出脚本复核。
- README 最终 polish。
- 压缩一版面试讲稿。
