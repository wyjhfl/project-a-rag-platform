# A-v2.7 Bad Cases

## 范围

A-v2.7 是面试材料压缩，不新增业务能力。

本轮 bad case 只记录表达风险。

## Case 1：材料完整但临场表达过长

现象：

A-v2.6 后证据链已经完整，但材料分散在 README、demo script、final delivery index 和 interview guide 中。

风险：

- 面试时容易从细节开始讲，前 2 分钟没有给出项目价值。
- 过早展开 provider、多模态、OCR 细节，导致主线不清。

处理：

- 新增 `docs/interview_pitch_pack.md`。
- 固化 2 分钟、5 分钟、15 分钟三种讲法。
- 高频追问单独整理，避免主讲时塞入过多防守细节。

## Case 2：边界讲法容易显得像失败

现象：

PaddleOCR runtime compatibility boundary、MiMo 非默认主链等内容如果表达不好，容易被理解为能力失败。

风险：

- 面试官误以为多模态整体不可用。
- 面试官误以为 MiMo 没转绿。

处理：

- 将边界表达改成“分组件验收”和“默认演示策略”。
- 明确 Vision LLM / MinerU Linux sliced 已转绿。
- 明确 MiMo v2.5 是候选 provider，对外默认 DeepSeek 是稳定性选择。

结论：

边界不是扣分点，讲清楚反而体现工程可信度。
