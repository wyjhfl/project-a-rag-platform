# A-v3.0 最终公开发布复核

## 目标

本轮目标是把 A-v2.9 的评测质量提升成果同步到公开发布版本，并确认公开仓库根目录形态仍然可验证、可演示、可面试讲述。

公开发布口径：

```text
sqlite + chroma + deepseek-chat + FastAPI + Vue 验收中心
```

默认发布版本不要求 PostgreSQL、Redis、Milvus、Neo4j 或 PaddleOCR 启动。

## 复核内容

- A-v2.9 真实评测报告已刷新：
  - 回归：`30/30`
  - 对抗：`20/20`
  - RAGAS 风格：`faithfulness=0.6983`
  - RAGAS 风格：`context_precision=0.8667`
  - RAGAS 风格：`context_recall=0.9778`
- A-v2.9 文档已进入公开导出脚本：
  - `docs/A-v2.9-evaluation-quality-review.md`
  - `docs/A-v2.9_bad_cases.md`
- README 和最终交付索引已更新到 A-v2.9 后状态。
- 公开导出脚本已保留 demo 启停脚本、评测数据、核心报告、前端截图和验收中心材料。

## 本地验证命令

```powershell
python backend\scripts\run_regression.py --cases data\eval\real_regression_cases_v1.json --docs-dir data\real_manuals_sanitized
python backend\scripts\run_adversarial.py --cases data\eval\real_adversarial_cases_v1.json --docs-dir data\real_manuals_sanitized
python backend\scripts\evaluate_ragas.py --cases data\eval\real_regression_cases_v1.json --docs-dir data\real_manuals_sanitized

python -m pytest backend\tests\test_agentic_rag.py backend\tests\test_rag_pipeline.py backend\tests\test_rag_security.py -q
$env:STORAGE_BACKEND='sqlite'; $env:VECTOR_BACKEND='chroma'; $env:CACHE_ENABLED='false'; $env:GRAPH_RETRIEVAL_ENABLED='false'; python -m pytest backend\tests\test_real_data_pipeline.py backend\tests\test_release_scenarios.py -q
python -m compileall backend\app\rag backend\scripts\evaluate_ragas.py backend\scripts\run_adversarial.py backend\scripts\create_public_release_repo.py
python backend\scripts\create_public_release_repo.py --target tmp\public-release-check-v30 --force
```

## 结论

A-v3.0 的发布重点不是新增功能，而是确认 A-v2.9 的质量成果已经成为公开交付版本的一部分。

面试时可以这样收束：

> 我最终没有停在“能跑 demo”，而是把真实资料评测扩容并固化到公开仓库。当前公开版本可以直接展示 30 条真实回归、20 条对抗测试和 RAGAS 风格指标，能证明系统在召回、上下文精度和幻觉边界上有可量化证据。

