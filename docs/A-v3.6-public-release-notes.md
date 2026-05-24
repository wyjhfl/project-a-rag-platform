# A-v3.6 公开交付 Release Notes

## Release

```text
tag: v3.5-public-delivery
date: 2026-05-24
repo: https://github.com/wyjhfl/project-a-rag-platform
```

## 发布定位

Project A 当前公开交付版本定位为：

> 企业设备售后诊断与工单闭环 RAG 平台，面向 AI 大模型 / RAG 开发求职展示，重点展示可引用回答、可评测质量、可追踪诊断链路、可解释边界和可本地演示能力。

## 核心能力

- 设备售后诊断 RAG 主链。
- grounded 回答与引用证据。
- Provider auth / grounded acceptance 验收。
- Vision LLM 与 MinerU Linux sliced 多模态转绿证据。
- PaddleOCR runtime compatibility boundary。
- evaluation、bad case、trace 和原始 JSON 证据链。
- 工单创建、人工升级、备件查询和闭环状态。
- Vue 前端验收中心。
- 本地 demo 启停脚本。
- 简历、作品集和面试投递材料。

## 质量指标

A-v2.9 后的真实评测结果：

```text
real regression: 30/30
real adversarial: 20/20
context_precision: 0.8667
faithfulness: 0.6983
context_recall: 0.9778
```

幻觉缓解覆盖：

- 未知型号拒答。
- 无型号/缺故障码时要求补充信息。
- 跨设备相似故障过滤。
- 危险操作触发停机、隔离和人工确认表达。

## 默认 Demo 画像

```text
sqlite + chroma + deepseek-chat + FastAPI + Vue 演示中心
```

默认 demo 不要求 PostgreSQL、Redis、Milvus、Neo4j 或 PaddleOCR。

## 已知边界

- `deepseek_chat` 是公开 demo 默认文本主链。
- `mimo-v2.5` 是候选 provider 对照，不作为默认现场链路。
- PaddleOCR 已正式列为 runtime compatibility boundary。
- 企业增强组件保留代码入口和部分验收证据，但不是公开 demo 前提。

## 验证记录

A-v3.5 最终远端巡检已确认：

```text
GitHub Actions CI: completed successfully
latest audited commit: b63676c662d54b31dd46622bbceb33149a9dc930
README includes: 作品集摘要 / 简历投递口径 / 30/30 / 20/20
```

A-v3.6 本轮目标：

- 补 release notes。
- 将 release notes 纳入公开发布包。
- 创建并推送 `v3.5-public-delivery` tag。

## 推荐阅读

- [README](../README.md)
- [最终交付索引](final_delivery_index.md)
- [A-v3.5 远端最终巡检](A-v3.5-final-remote-audit.md)
- [A-v3.4 简历投递材料收口](A-v3.4-resume-delivery-pack.md)
- [A-v2.9 评测质量提升复盘](A-v2.9-evaluation-quality-review.md)
