# A-v3.3 轻量作品集入口增强

## 本轮目标

把 Project A 的公开仓库入口从“能解释项目”进一步压缩成“能被快速扫读和引用”。

本轮不新增功能，不改 RAG 主链，不改评测逻辑，只增强 README 首屏的作品集表达。

## 改动内容

- `README.md`
  - 新增 “作品集摘要”。
  - 将项目定位、技术栈、工程闭环和 A-v2.9 质量指标压缩到一个短段落。
  - 当前阶段更新为 A-v3.3。
- `docs/final_delivery_index.md`
  - 新增 A-v3.3 证据入口。
- `backend/scripts/create_public_release_repo.py`
  - 将 A-v3.3 文档纳入公开发布包。

## 作品集摘要口径

可直接引用：

> Project A 是一个企业设备售后诊断 RAG 平台，把设备型号、故障码和现场现象转成可引用的排障建议，并在资料不足或高风险操作时拒答/升级人工。项目覆盖 FastAPI、Vue、Chroma、SQLite、LangChain/LangGraph、Provider 验收、多模态边界、evaluation、bad case、trace 和工单闭环。A-v2.9 后真实回归扩容到 `30/30`、真实对抗扩容到 `20/20`，并达到 `context_precision=0.8667`、`faithfulness=0.6983`、`context_recall=0.9778`。

## 为什么需要这一轮

README 已经能完整说明项目，但作品集和简历场景更强调快速判断：

- 做了什么业务场景。
- 技术栈是否贴近岗位。
- 是否有可量化验收结果。
- 是否能体现工程闭环，而不只是聊天 demo。

A-v3.3 把这些信息前置到首屏，减少招聘方首次阅读成本。

## 验收方式

```powershell
python backend/scripts/create_public_release_repo.py --target tmp/public-release-check-v33 --force
```

预期：

- README 首屏出现 “作品集摘要”。
- `docs/A-v3.3-portfolio-entry-review.md` 进入公开发布包。
- 最终交付索引能跳转到 A-v3.3 复盘。

## 下一步

A-v3.4 建议继续把材料压缩成三种投递口径：

- 简历 bullet。
- GitHub pinned repo 描述。
- 面试 30 秒开场白。
