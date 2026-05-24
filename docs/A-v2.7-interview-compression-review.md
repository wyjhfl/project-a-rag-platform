# A-v2.7 面试材料压缩版复盘

## 本轮目标

A-v2.7 不新增业务能力，目标是把 Project A 的完整证据链压缩成面试可用表达。

本轮重点：

- 2 分钟自我介绍版。
- 5 分钟演示版。
- 15 分钟技术深挖版。
- 高频追问回答。
- 面试反问和收束句。

## 本轮边界

不做：

- 不改 RAG 主链。
- 不新增 demo 截图。
- 不重新跑 provider 或多模态验收。
- 不修改前端交互。

只做：

- 面试表达压缩。
- 文档索引同步。
- 公开导出清单补充。
- 最小文档一致性检查。

## 核心产物

新增：

- `docs/interview_pitch_pack.md`
- `docs/A-v2.7-interview-compression-review.md`
- `docs/A-v2.7_bad_cases.md`

更新：

- `README.md`
- `docs/final_delivery_index.md`
- `docs/dev_log.md`
- `docs/debug_log.md`
- `backend/scripts/create_public_release_repo.py`

## 面试主线

推荐主线：

```text
业务场景
-> RAG 主链
-> grounded 验收
-> provider 对比
-> 多模态边界
-> evaluation / bad case / trace
-> 前端验收中心
-> 当前边界和下一步
```

## 当前口径

一句话：

> Project A 是一个设备售后诊断 RAG 工程系统，重点不是只让模型回答，而是让每条能力都有验收状态、证据文件、失败边界和演示入口。

默认 demo：

```text
sqlite + chroma + deepseek-chat
```

候选 provider：

```text
mimo-v2.5
```

明确边界：

```text
PaddleOCR = runtime compatibility boundary
```

## 验收方式

本轮主要验证文档一致性：

- README 能找到面试压缩包。
- final delivery index 能找到面试压缩包。
- 公开导出脚本包含 A-v2.7 文档。
- 旧的 “MiMo 认证未转绿” 口径不再作为当前结论出现。

## 验证结果

文档一致性检查：

```text
README.md -> docs/interview_pitch_pack.md
docs/final_delivery_index.md -> docs/interview_pitch_pack.md
backend/scripts/create_public_release_repo.py -> A-v2.7 docs
```

旧口径扫描：

```text
未发现旧 MiMo 认证阻塞说法作为当前结论残留。
```

脚本验证：

```text
python -m compileall backend\scripts\create_public_release_repo.py
passed
```

公开导出 dry run：

```text
python backend\scripts\create_public_release_repo.py --target tmp\public-release-check --force
passed
```

导出包已确认包含：

- `docs/interview_pitch_pack.md`
- `docs/A-v2.7-interview-compression-review.md`
- `docs/A-v2.7_bad_cases.md`

## 面试讲法

> A-v2.7 我做的是表达压缩。因为项目已经有真实验收和演示证据，面试时真正需要的是按时间长短讲清重点：2 分钟讲项目价值，5 分钟讲演示路线，15 分钟讲技术决策和边界。

## 下一步

推荐进入 A-v2.8 作品集视觉补图：

- provider 状态截图。
- 多模态状态截图。
- evaluation + trace 截图。
- trace JSON 弹层截图。
- provider comparison 摘要截图。
