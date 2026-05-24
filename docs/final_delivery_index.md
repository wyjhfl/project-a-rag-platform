# A-v2.6 最终交付索引

## 目标

把 Project A 的公开展示入口收成一条稳定链路：

```text
README
-> 本地 demo 启动
-> 前端验收中心
-> 演示脚本和截图
-> provider / 多模态 / evaluation 证据
-> bad case 和 trace
-> 面试讲法
```

这份索引用于作品集展示、面试前自检和公开仓库导出前复核。

## 推荐阅读顺序

1. 项目入口：[README.md](../README.md)
2. 启动指南：[docs/demo_guide.md](demo_guide.md)
3. 五分钟演示路线：[docs/five_min_demo_route.md](five_min_demo_route.md)
4. 标准演示脚本：[docs/demo_script.md](demo_script.md)
5. 面试讲法索引：[docs/interview_guide.md](interview_guide.md)
6. 面试材料压缩包：[docs/interview_pitch_pack.md](interview_pitch_pack.md)
7. 公开交付 checklist：[docs/public_delivery_checklist.md](public_delivery_checklist.md)

## 当前公开 demo 画像

```text
sqlite + chroma + deepseek-chat + FastAPI + Vue 验收中心
```

默认演示不依赖 PostgreSQL、Redis、Milvus、Neo4j 或 PaddleOCR。

## 必讲能力

文本主链：

- `deepseek_chat` 是当前公开 demo 默认主链。
- A-v2.2 已确认 MiMo token-plan 口径可进入 grounded 比较。
- A-v2.4 后保留 `mimo-v2.5` 作为候选 provider 对照，不作为默认现场演示链路。

多模态：

- Vision LLM 已转绿。
- MinerU Linux sliced 已转绿。
- PaddleOCR 已定性为 runtime compatibility boundary。

工程闭环：

- evaluation 负责回归评价。
- bad case 负责沉淀失败样本。
- trace 负责定位召回、上下文、rerank 和答案决策链路。
- 前端验收中心负责把真实报告聚合成可展示状态。
- A-v2.9 已将真实回归扩容到 `30/30`，真实对抗扩容到 `20/20`，并将 RAGAS 风格 `faithfulness` 提升到 `0.6983`。

## 核心证据入口

Provider：

- [A-v2.2 Provider 验收报告](A-v2.2_provider_acceptance_report_2026-05-23.json)
- [A-v2.4 Provider 对比 JSON](A-v2.4_provider_comparison_report_2026-05-23.json)
- [A-v2.4 Provider 对比复盘](A-v2.4-provider-comparison-review.md)

多模态：

- [A-v1.5 多模态验收报告](A-v1.5_multimodal_acceptance_report_2026-05-20.json)
- [A-v2.3 PaddleOCR 兼容性报告](A-v2.3_paddleocr_compatibility_report_2026-05-23.json)
- [A-v2.3 PaddleOCR 兼容性复盘](A-v2.3-paddleocr-compatibility-review.md)

评测与 bad case：

- [A-real-data RAGAS 报告](A-real-data_ragas_report.json)
- [A-real-data 回归报告](A-real-data_regression_report.json)
- [A-real-data 对抗报告](A-real-data_adversarial_report.json)
- [A-real-data bad cases](A-real-data_bad_cases.md)
- [A-v2.9 评测质量提升复盘](A-v2.9-evaluation-quality-review.md)
- [A-v2.9 bad cases](A-v2.9_bad_cases.md)

演示交付：

- [A-v2.1 演示与交付收口复盘](A-v2.1-demo-delivery-review.md)
- [A-v2.5 演示素材补强复盘](A-v2.5-demo-assets-review.md)
- [A-v2.6 公开交付检查复盘](A-v2.6-public-delivery-review.md)
- [A-v2.7 面试材料压缩版复盘](A-v2.7-interview-compression-review.md)
- [A-v2.8 作品集视觉补图复盘](A-v2.8-portfolio-visual-assets-review.md)
- [A-v2.9 评测质量提升与样本扩容复盘](A-v2.9-evaluation-quality-review.md)
- [A-v3.0 最终公开发布复核](A-v3.0-public-release-verification.md)
- [A-v3.1 公开展示与面试讲法收口](A-v3.1-public-readability-review.md)
- [A-v3.2 远端 CI 与公开展示复核](A-v3.2-remote-ci-display-review.md)
- [A-v3.3 轻量作品集入口增强](A-v3.3-portfolio-entry-review.md)
- [A-v3.4 简历投递材料收口](A-v3.4-resume-delivery-pack.md)

面试材料：

- [面试讲法索引](interview_guide.md)
- [面试材料压缩包](interview_pitch_pack.md)

## 截图资产

当前已生成：

- [A-v2.5 demo 首页截图](assets/a-v2.5/01-demo-home.png)
- [Provider 状态截图](assets/a-v2.5/02-provider-status.png)
- [多模态状态截图](assets/a-v2.5/03-multimodal-status.png)
- [Evaluation Trace 截图](assets/a-v2.5/04-evaluation-trace.png)
- [Trace JSON 截图](assets/a-v2.5/05-trace-json.png)
- [Provider 对比摘要截图](assets/a-v2.5/06-provider-comparison-report.png)

## 公开导出前检查

执行：

```powershell
python backend/scripts/create_public_release_repo.py --target tmp/public-release-check --force
```

检查重点：

- 不复制 `.env`。
- `.env.demo.example` 不含真实 key。
- A-v2.2 到 A-v2.6 的核心文档和 JSON 进入导出包。
- demo 启停脚本进入导出包。
- 运行材料能从 README 找到。

## 当前结论

Project A 已经从研发态进入可交付作品态。

最稳的公开表达是：

> 这是一个设备售后诊断 RAG 工程系统，默认 demo 可本地启动，前端可展示真实验收状态，Provider 和多模态能力都有证据链，未转绿能力有明确边界。
