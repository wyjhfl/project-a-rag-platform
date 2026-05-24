# A-v3.4 简历投递材料收口

## 本轮目标

把 Project A 的项目表达压缩成三种可以直接用于投递的材料：

- 简历 bullet。
- GitHub pinned repo 描述。
- 30 秒面试开场白。

本轮不新增功能，不修改 RAG 主链，只做投递表达收口。

## 简历 Bullet

推荐版本：

- 企业设备售后诊断 RAG 平台，基于 FastAPI、Vue、Chroma、SQLite、LangChain/LangGraph 实现可引用问答、Provider 验收、多模态边界、bad case、trace、evaluation 与工单闭环；真实回归扩容至 `30/30`，真实对抗扩容至 `20/20`，RAGAS 风格指标达到 `context_precision=0.8667`、`faithfulness=0.6983`、`context_recall=0.9778`。

更短版本：

- 企业设备售后诊断 RAG 平台：支持 grounded 回答、引用证据、Provider 验收、evaluation、trace、bad case 与工单闭环；真实回归 `30/30`、真实对抗 `20/20`。

偏工程版本：

- 构建可本地演示的 RAG 工程闭环：FastAPI + Vue + Chroma + SQLite + LangChain/LangGraph，覆盖检索、grounded 生成、引用、评测、trace、bad case、人工升级和发布 CI。

## GitHub Pinned Repo 描述

英文短描述：

```text
Equipment after-sales diagnosis RAG platform with grounded answers, citations, evaluation, trace, provider acceptance, multimodal boundaries, and ticket workflow.
```

中文短描述：

```text
企业设备售后诊断 RAG 平台：可引用问答、评测、trace、Provider 验收、多模态边界与工单闭环。
```

如果只能写一句：

```text
Grounded RAG platform for equipment after-sales diagnosis, evaluation, trace, and ticket workflow.
```

## 30 秒面试开场白

推荐版本：

> 我做的 Project A 是一个企业设备售后诊断 RAG 平台，不是普通聊天 demo。它从设备型号、故障码和现场现象出发，完成知识检索、引用回答、grounded 校验、evaluation、bad case、trace 和工单/人工升级闭环。为了证明质量，我把真实回归扩容到 `30/30`、真实对抗扩容到 `20/20`，并把未知型号、资料不足、跨设备混淆和危险操作都纳入幻觉缓解测试。

更短版本：

> Project A 把设备售后诊断做成了可检索、可引用、可评测、可追踪、可演示、能升级人工的 RAG 工程闭环。它不是只接一个聊天接口，而是有真实 Provider 验收、多模态边界、bad case、trace 和量化评测结果。

## 投递时怎么用

- 简历项目经历：用 “推荐版本” bullet。
- GitHub pinned repo：用英文短描述。
- 面试开场：用 30 秒推荐版本。
- 技术深挖：跳转到 `docs/interview_pitch_pack.md`。
- 证据链追溯：跳转到 `docs/final_delivery_index.md`。

## 验收方式

```powershell
python backend/scripts/create_public_release_repo.py --target tmp/public-release-check-v34 --force
```

预期：

- README 首屏出现 “简历投递口径”。
- `docs/A-v3.4-resume-delivery-pack.md` 进入公开发布包。
- 最终交付索引能跳转到 A-v3.4。

## 下一步

A-v3.5 建议做远端最终巡检：

- README 首屏和投递材料是否一致。
- GitHub Actions 是否继续通过。
- 核心文档链接是否仍全部可打开。
