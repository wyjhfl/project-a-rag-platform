# A-v2.9 评测质量提升与样本扩容复盘

## 目标

本轮把已有评测体系从“有报告”推进到“样本更多、指标更稳、幻觉风险更可控”。

验收目标：

- 真实回归测试不少于 30 条，并全部通过。
- 真实对抗测试不少于 20 条，并全部通过。
- RAGAS 风格指标达到：
  - `faithfulness >= 0.55`
  - `context_precision >= 0.70`
  - `context_recall >= 0.85`

## 实现内容

- `data/eval/real_regression_cases_v1.json` 从 20 条扩容到 30 条。
- `data/eval/real_adversarial_cases_v1.json` 从 10 条扩容到 20 条。
- 语义切片保留章节标题，避免故障码只出现在标题时丢失上下文召回。
- 故障码识别支持 `UV-1`、`BAT-VOLT`、`COM-08` 等多字母代码。
- 检索评分补充安全、欠压、压差、短路、释放压力等售后意图。
- 安全回答统一补充“禁止/不建议、停机或隔离、检查、人工确认”。
- 对抗评测开始记录关键词命中情况，避免只看类别粗略通过。
- RAGAS 风格 faithfulness 改为基于项目统一 tokenization，避免中文连续文本被低估。

## 真实结果

```text
real regression:
case_count = 30
passed_count = 30
source_hit_count = 30

real adversarial:
case_count = 20
passed_count = 20

real RAGAS-style:
faithfulness = 0.6983
answer_relevancy = 0.9222
context_precision = 0.8667
context_recall = 0.9778
low_score_case_count = 3
```

## 技术结论

本轮主要收益不是“多加测试样本”，而是把评测失败暴露出的真实链路问题补进主链：

- 标题级故障码进入 chunk 内容后，`context_recall` 从 `0.8222` 提升到 `0.9778`。
- 同设备、同故障码和售后意图加权后，跨设备上下文噪声明显减少。
- 危险操作和未知资料场景更稳定地走安全边界或资料不足拒答。
- RAGAS 风格评测对中文回答更公平，不再因为中文没有空格而系统性低估 faithfulness。

## 面试讲法

可以这样讲：

> 我没有只做一次 demo，而是把真实脱敏资料做成回归集和对抗集。A-v2.9 后，真实回归从 20 条扩到 30 条并全部通过，对抗从 10 条扩到 20 条并全部通过；同时把章节标题里的故障码纳入 chunk，提升上下文召回，并通过安全边界压制未知型号和危险操作场景的幻觉。

