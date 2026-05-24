# A-v2.1 演示与交付收口复盘

## 本轮目标

A-v2.1 不新增底层 RAG 能力，目标是把已经完成的文本主链、多模态验收、演示中心、bad case、trace 和 demo 脚本整理成稳定交付形态。

本轮核心问题：

```text
项目已经能跑、能验收、能展示
但还需要统一入口、演示顺序、面试讲法和交付记录
```

## 本轮边界

本轮不做：

- 不改 RAG 检索链路。
- 不改 LLM 生成逻辑。
- 不改多模态 runtime。
- 不修 MiMo。
- 不修 PaddleOCR。
- 不新增前端功能。

本轮只做：

- README 对外入口整理。
- demo 启动指南。
- 标准演示脚本。
- 面试讲法索引。
- 版本复盘和日志记录。
- demo 链路真实验证。

## 当前推荐演示画像

```text
sqlite + chroma + deepseek-chat + FastAPI + Vue 演示中心
```

推荐原因：

- sqlite / chroma 本地稳定。
- deepseek_chat 已通过 grounded 验收。
- 企业增强依赖不会阻塞公开演示。
- 前端演示中心已经能展示 provider、多模态、evaluation、bad case 和 trace。

## 当前能力状态

已转绿：

- `deepseek_chat`：真实文本 LLM 主链候选，已通过 grounded 验收。
- `Vision LLM`：真实视觉链路可用。
- `MinerU Linux sliced`：小页范围真实 PDF 解析可用。
- `acceptance overview`：后端可聚合验收证据。
- 前端演示中心：可展示 trace 详情和原始 JSON。

明确边界：

- `MiMo`：认证 / 接入层未转绿，暂不做能力结论。
- `PaddleOCR`：runtime_incompatible。
- MinerU 整本长文档：CPU profile 下仍有吞吐和超时边界。
- 企业增强依赖：不是公开 demo 默认启动前提。

## 本轮产物

新增：

- `docs/demo_guide.md`
- `docs/demo_script.md`
- `docs/interview_guide.md`
- `docs/A-v2.1-demo-delivery-review.md`

更新：

- `README.md`
- `docs/dev_log.md`
- `docs/debug_log.md`

## 如何演示

启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_demo_stack.ps1 -StopExisting
```

访问：

```text
http://127.0.0.1:4175/
```

讲解顺序：

1. 项目定位。
2. demo 画像。
3. 系统状态。
4. 验收中心。
5. 文本 LLM 主链。
6. 多模态状态。
7. evaluation / bad case / trace。
8. 当前边界。
9. 下一步规划。

## 面试讲法

推荐主线：

> 我不是只做了一个 RAG 问答接口，而是把设备售后诊断做成了有证据、有验收、有 bad case、有 trace、有前端演示中心的工程闭环。

重点讲：

- grounded acceptance 如何防幻觉。
- provider 验收如何区分认证、配置和回答质量。
- 多模态验收如何按组件拆分。
- bad case 和 trace 如何定位低分样本。
- 演示中心如何把真实报告产品化。

## 验证记录

本轮已验证：

```text
GET http://127.0.0.1:18082/health -> 200
GET http://127.0.0.1:18082/api/v1/system/status -> 200
GET http://127.0.0.1:18082/api/v1/acceptance/overview -> 200
GET http://127.0.0.1:4175/ -> 200
GET http://127.0.0.1:4175/api/v1/acceptance/overview -> 200
```

启动命令：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_demo_stack.ps1 -StopExisting
```

结论：

```text
A-v2.1 demo 交付路径真实可运行。
```

## 下一步衔接

推荐继续：

1. **A-v2.2 MiMo 重新验收**：先解决认证 / 接入层，再做真实 provider 对比。
2. **A-v2.3 PaddleOCR 兼容性专项**：切 Docker/Linux runtime 或正式固化环境边界。
3. **A-v2.4 演示素材补强**：补截图、短录屏和公开仓库导出说明。
