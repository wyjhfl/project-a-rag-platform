# A-v2.8 Bad Cases

## 范围

A-v2.8 是作品集视觉补图，不新增业务能力。

本轮 bad case 只记录截图与展示风险。

## Case 1：Trace JSON 截图被遮罩影响可读性

现象：

首次截取 `05-trace-json.png` 时使用整页截图，画面里弹层遮罩和页面滚动状态叠在一起，JSON 内容不够清晰。

影响：

- 作品集里看不清 trace JSON 的结构。
- 面试展示时不利于讲 raw trace 证据。

处理：

- 改为只截 `.el-dialog` 弹层本体。
- 重新生成 `05-trace-json.png`。

结论：

截图质量问题已修复，不影响 demo 功能。

## Case 2：Provider comparison Markdown 原文截图展示效果差

现象：

首次 `06-provider-comparison-report.png` 直接打开 Markdown 原文截图，画面像纯文本，不适合作品集展示。

影响：

- 指标虽然真实，但视觉表达弱。
- 不利于一眼看出默认主链和候选 provider 的决策。

处理：

- 基于 A-v2.4 真实指标重制英文摘要图。
- 保留 DeepSeek 默认、MiMo v2.5 候选、MiMo v2.5 Pro 暂不默认的决策。

结论：

截图表达已改善，数据口径仍来自真实验收报告。
