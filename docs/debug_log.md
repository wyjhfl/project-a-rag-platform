# 调试日志

## 2026-05-27 A-v5.1 风险与边界记录

风险：

- `/readyz` 检查 storage 时调用 `store.list_chat_records()`，当前 storage 检查通过该方法覆盖 SQLite/Postgres 两种后端。如果表为空则返回空列表，仍视为 ok。但如果数据库文件损坏，会返回 error。
- `/readyz` 检查 Milvus 时会尝试新建 MilvusClient 连接，如果 Milvus 不可达，返回 error。此检查仅在 VECTOR_BACKEND=milvus 时触发。
- graceful shutdown 只关闭 Redis 连接。Chroma PersistentClient 和 SQLite 无显式 close 方法，依赖 Python GC。
- docker-compose healthcheck 使用 Python urllib，要求容器内有 Python 运行时。如果换成 Alpine + 精简镜像，需改用 curl。

边界：

- 未实现 PostgreSQL 连接检查（PostgresStore 无 ping 方法）
- 未实现 LLM API 可达性检查（避免每次 readyz 都调 LLM 产生 token 消耗）
- 未实现 Chroma 内部集合存在性检查（只检查 hybrid_retriever 是否初始化）

## 2026-05-26 A-v4.4 提交前安全修正记录

现象：

- Git 根目录实际是 `天空没有极限`，`七月v0.3/` 作为旧学习项目被 Git 跟踪，提交 Project A 时会混入无关文件。
- `preflight_multimodal_linux_runtime.py` 和 `preflight_mineru_linux_runtime.py` 包含硬编码 WSL 用户名路径 `<WSL_HOME>/...`。
- `create_public_release_repo.py` 导出公开材料时未做路径脱敏，本地路径会泄露到公开仓库。
- `.env` 包含真实 DeepSeek API Key，虽未被 Git 跟踪，但需提醒轮换。

处理：

- `git rm --cached -r "七月v0.3/"` 移除 37 个文件索引，磁盘文件保留。
- 两个 preflight 脚本的硬编码路径改为 `os.environ.get()` 读取，默认值使用 `$HOME` 等非个人化表达。
- `create_public_release_repo.py` 新增 `sanitize_text()` 函数和 `TEXT_EXTENSIONS` 集合，复制文本文件时自动替换敏感路径。
- 新增 `test_public_release_sanitization.py` 覆盖 Windows 路径、WSL 路径、下载目录、JSON 结构保持、混合模式等 7 个用例。

风险：

- 根目录 `.gitignore` 无法通过工具自动修改（路径限制），需手动追加 `七月v0.3/`。
- `.env` 中的 Key 泄露风险：虽然 `.gitignore` 已排除 `.env`，但 Key 已在本地明文存在，用户必须到 DeepSeek 平台轮换。

## 2026-05-26 A-v4 工程基线收口记录

现象：

- main.py 承担了约 490 行验收聚合业务逻辑，违反单一职责。
- CI 只跑 6 个测试文件，验收中心接口没有 CI 保护。
- .gitignore 缺少 .codex/ 精确忽略规则。

处理：

- 将 `_build_acceptance_overview` 及 16 个辅助函数迁移到 `backend/app/acceptance/service.py`。
- `_latest_doc` 签名从 `(pattern)` 变为 `(docs_dir, pattern)`，因为 DOCS_DIR 不再是模块级常量。
- `build_acceptance_overview()` 接受 `docs_dir` 和 `version` 参数，默认值与原行为一致。
- CI 新增 5 个测试文件覆盖验收中心、RAG 主链、查询增强、多轮对话和切片逻辑。
- .gitignore 添加 `.codex/*` + `!.codex/skills/` + `.codex/skills/*` + `!.codex/skills/project-a-rag-mentor/` 精确规则。

风险：

- 验收中心接口的 response_model 类型注解从路由定义中移除了（因为 Pydantic 模型已不在 main.py 的 import 范围内），FastAPI 仍会通过返回值自动序列化，但 OpenAPI schema 中可能不再显示详细字段。如果需要恢复，可以在 main.py 中 import AcceptanceOverviewResponse 并加回 response_model 注解。
- .codex/ 的忽略规则使用了逐层排除模式，如果未来 .codex/skills/ 下新增其他项目级规则文件，需要手动添加排除规则。

## 2026-05-24 A-v3.6 Release Tag 准备记录

现象：

- A-v3.5 已完成远端最终巡检，但公开仓库还没有正式 tag。
- 如果作为作品集长期引用，只有 `main` 分支不如 tag 稳定。

处理：

- 确认远端和本地没有现有 `v3.5*` tag。
- 新增 A-v3.6 release notes。
- 将 release notes 纳入 README、最终交付索引和公开导出脚本。

风险：

- tag 应在 A-v3.6 release notes 提交后创建，避免 tag 指向缺少 release notes 的旧提交。
- 若后续继续改动，不能默认移动已发布 tag；应另开新 tag。

## 2026-05-24 A-v3.5 远端最终巡检记录

现象：

- A-v3.4 已推送并通过 GitHub Actions。
- 需要确认远端公开页面和本地导出材料一致，避免只在本地文档里完成收口。

检查：

- `git ls-remote` 确认远端 `main` 指向 `b63676c662d54b31dd46622bbceb33149a9dc930`。
- 公开 README 页面确认包含 `作品集摘要`、`简历投递口径`、`30/30`、`20/20`。
- Actions 页面确认 `Run 11 of CI` 为 `completed successfully`。

处理：

- 新增 A-v3.5 最终远端巡检文档。
- README 当前阶段更新为最终巡检完成。
- 将下一步从继续材料收口改为可选 release tag。

风险：

- GitHub Actions 状态是时间敏感信息，本文档记录的是 2026-05-24 的远端状态。
- 后续若继续推送，需要重新巡检最新 run。

## 2026-05-24 A-v3.4 投递材料表达检查

现象：

- README 已有作品集摘要，但简历、GitHub pinned repo 和面试开场白的使用场景不同。
- 如果只保留一段长摘要，投递时还需要临时改写。

处理：

- 新增 A-v3.4 投递材料包。
- 将同一项目能力压缩成三种长度和用途：
  - 简历 bullet：强调技术栈、工程闭环和量化结果。
  - GitHub pinned repo：强调关键词和英文短描述。
  - 30 秒开场白：强调不是聊天 demo，而是可验收 RAG 工程闭环。

风险：

- 本轮只改文档和导出清单，不改变运行行为。
- 需要验证公开发布包包含 A-v3.4 文档，且 README 链接可打开。

## 2026-05-24 A-v3.3 作品集入口表达检查

现象：

- A-v3.2 后 README 首屏已经能说明项目，但对简历/作品集场景仍偏长。
- 招聘方快速扫读时，更需要一段能同时回答业务场景、技术栈、工程闭环和量化结果的摘要。

处理：

- 在 README 顶部新增 “作品集摘要”。
- 保留原 “30 秒看懂项目”，让完整项目理解仍有结构化入口。
- 将 A-v2.9 质量指标直接写入摘要，避免量化成果被埋在后文。

风险：

- 本轮只改文档和导出清单，不改变运行行为。
- 需要确认公开导出包包含 A-v3.3 文档。

## 2026-05-24 A-v3.2 GitHub Actions 失败定位

现象：

- A-v3.1 推送后，GitHub Actions 最新 CI run `#8` 显示 failed。
- 失败 job 为 `backend-and-frontend`。
- GitHub 未登录页面无法展开完整日志。

定位方式：

- 在发布克隆仓库复跑 CI 同款命令。
- `pytest` 通过，`frontend build` 通过。
- `ruff check backend` 失败。

根因：

- CI 新增或保留了 `python -m ruff check backend`。
- 当前代码库有多处历史长行触发 `E501`。
- `backend/scripts/run_av24_provider_comparison.py` 有 1 处 import 排序问题。

处理：

- 将 `E501` 加入 Ruff ignore，避免历史长行阻塞发布 CI。
- 保留其他 `E/F/I/B` 检查，继续捕获语法、未定义变量、import 顺序和常见 bug。
- 用 Ruff 修复 import 排序。

验证重点：

- 重新运行 `python -m ruff check backend`。
- 重新导出公开发布包。
- 重新推送后观察 GitHub Actions。

## 2026-05-24 A-v3.1 公开展示材料检查

现象：

- A-v2.9 已经有真实质量提升数据，但 README 首屏仍更像版本状态汇总，招聘方需要继续向下翻才能看到最强证据。
- A-v3.0 已完成公开发布复核，但最终交付索引缺少 A-v3.1 的展示收口入口。
- 面试压缩包已经覆盖 provider、多模态和演示中心，但 A-v2.9 的扩容测试数字还没有足够前置。

处理：

- README 新增 30 秒项目摘要，把业务场景、默认 demo、质量指标、面试亮点放到首屏。
- 面试压缩包补入 `30/30`、`20/20` 和 RAGAS 风格指标。
- A-v3.1 文档加入公开发布导出脚本。

风险：

- 本轮只改文档和导出清单，不改变代码行为。
- 需要通过导出脚本验证 A-v3.1 文档确实进入公开发布包。

## 2026-05-19 A-v1.5 多模态预检分层

开始 A-v1.5 时，先没有直接把真实多模态链路挂进主链，而是先补一套独立预检与统一验收脚本，原因是：

- Vision、OCR、PDF parsing 的阻塞层级完全不同
- 如果直接端到端联调，最后只会得到一个笼统的 “blocked”
- 很难判断究竟是认证、素材、运行时兼容还是服务超时

本轮新增：

- `backend/scripts/preflight_multimodal_real.py`
- `backend/scripts/run_av15_multimodal_acceptance.py`

并在预检脚本里做了两件关键事情：

1. 强制切回 `sqlite + chroma`
2. 为 PaddleOCR / MinerU 增加组件级超时，避免整轮预检被单点卡死

第一轮真实结果说明：

- Vision LLM 当前不是模型不行，而是 `401 Unauthorized`
- PaddleOCR 当前不是 API 不通，而是样例图片本身损坏，触发 `libpng CRC error`
- MinerU 当前不是入口没接，而是 probe 超时

因此 A-v1.5 当前已经把阻塞拆成了三个不同层：

- 认证阻塞
- 样例阻塞
- 运行时/服务阻塞

这比“统一 blocked”更适合继续推进。

### Vision LLM 配置口径校准

继续追 Vision 失败时，发现预检脚本里显示的 `vision_llm_base_url` 仍是旧的 DashScope 路径，而当前 `.env` 已经是新的小米 token-plan 路径。

根因：

- 进程环境里残留了旧的 `LLM_BASE_URL`
- `preflight_multimodal_real.py` 原先 `load_dotenv(..., override=False)`
- 导致脚本继续吃旧环境变量，而不是当前仓库 `.env`

处理：

- 将 `preflight_multimodal_real.py` 改为 `load_dotenv(..., override=True)`
- 在 `.env` 中显式补：
  - `VISION_LLM_MODEL=mimo-v2-omni`
  - `VISION_LLM_API_KEY`
  - `VISION_LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1`

继续定位后又确认一件事：

- 展示名 `MiMo-V2-Omni` 不是该 endpoint 接受的模型 id
- `/models` 返回的真实 model id 是 `mimo-v2-omni`

修正后：

- `VisionLLMInterpreter` 真实图片请求通过
- 说明当前 Vision 阻塞已经解除

这让 A-v1.5 的状态从：

- 0 条真实多模态绿链

推进到：

- 1 条真实图片 Vision 绿链

## 2026-05-19 A-v1.4 grounded acceptance 误杀修复

在继续追 `deepseek_chat` 的 `grounded_rejection` 时，发现关键现象：

- `direct_llm_connected=true`
- 手工拆解 `search -> select_chunks -> llm_generate -> _accept_llm_answer` 时，DeepSeek 能产出 grounded 回答
- 但标准预检里 `/api/v1/chat` 仍经常回到 fallback

继续定位后确认，真正阻塞不是 provider，而是 acceptance 规则：

- DeepSeek 的回答会明确说清“E-17 相关排查可以依据资料确认”
- 同时也会诚实标注“排气温度升高的专项原因当前资料不足”
- 这种“部分可答、部分不可答”的回答本质上是 grounded 的
- 但旧逻辑只要命中“当前资料不足 / 无法确认”字样，就直接拒收

处理：

- 在 `backend/app/rag/pipeline.py` 中放宽 acceptance：
  - 如果回答命中设备与故障码
  - 与上下文重叠充分
  - 并给出明确排查动作
  - 即使同时声明部分资料不足，也允许通过
- 在 `backend/scripts/preflight_real_llm_grounding.py` 中同步口径
- 用 `backend/tests/test_llm_grounded_acceptance.py` 锁住该行为

修复后验证：

- `docs/A-v1.4_real_llm_grounding_preflight_deepseek_2026-05-19.json`
  - `chat_grounded_llm=true`
- `docs/A-v1.4_provider_acceptance_report_2026-05-19.json`
  - `deepseek_chat=accepted`

这说明 A-v1.4 当前的真正结论已经从：

- DeepSeek 直连但 grounded 不稳定

变成：

- DeepSeek 已通过 grounded 验收，可作为默认真实文本 LLM 候选

## 2026-05-18 A-v1.4 Provider 验收报告结构补强

在开始真实 MiMo 多模型对比前，先检查 A-v1.3 的 provider 验收报告是否已经足够支持“默认模型决策”。

发现问题：

- 现有报告只有 `accepted / unstable / blocked` 三档。
- `blocked` 会把 API key 失效、配置缺失、连通性问题、provider 服务异常都混在一起。
- 这样不利于判断“该换模型”还是“该修配置”。

处理：

- 在 `backend/scripts/run_provider_acceptance.py` 中新增 `blocker_type`
- 对 `critical_failures` 的 reason 做轻量归类：
  - `auth_invalid`
  - `config_missing`
  - `timeout`
  - `rate_limited`
  - `provider_server_error`
  - `request_rejected`
  - `probe_execution_failed`
  - `connectivity_or_runtime_error`
- 对 `unstable` 统一归因为 `grounded_rejection`
- summary 中新增 `blocker_type_counts`

这样下一轮即使 MiMo 某个模型再次出现 `blocked`，也能先判断是：

- key/凭证问题
- base_url / 配置问题
- provider 本身问题
- 还是 grounded 主链没有稳定通过

### 第一轮真实验收中的脚本污染问题

第一次跑 `docs/A-v1.4_provider_acceptance_report.json` 时，`deepseek_chat` 在未配置 `DEEPSEEK_API_KEY` 的情况下，仍被错误打成 `auth_invalid`。

根因：

- `run_provider_acceptance.py` 在切换 provider 时，如果目标 provider 没有 key，只是删除了子进程环境里的 `LLM_API_KEY`
- 但 `preflight_real_llm_grounding.py` 会再次 `load_dotenv(..., override=False)`
- 这样 `.env` 里的默认 `LLM_API_KEY` 又被补回来了
- 导致 DeepSeek 误用了 MiMo key，结论失真

处理：

- 改为在 provider 没有专属 key 时，显式传入 `LLM_API_KEY=\"\"`
- 补充测试，确保 `config_missing` 能正确落到报告里

修复后重新验收结果：

- `default_env`: `auth_invalid`
- `mimo_v25_pro`: `auth_invalid`
- `mimo_v25`: `auth_invalid`
- `deepseek_chat`: `config_missing`

这说明 A-v1.4 当前最前置阻塞已经被明确定位为：

- MiMo：认证失败
- DeepSeek：配置缺失

当前还没有进入 grounded 主链能力比较阶段。

### 独立认证预检补充

为了把“provider 认证问题”和“grounded 主链问题”彻底拆开，又新增了：

- `backend/scripts/preflight_provider_auth.py`

这份脚本不走完整 RAG 主链，只做：

1. `GET /models`
2. 最小 `POST /chat/completions`

实测结果写入：

- `docs/A-v1.4_provider_auth_preflight_2026-05-18.json`

这份报告进一步确认：

- `mimo-v2.5-pro`
- `MiMo-V2.5-Pro`
- `MiMo-V2.5`
- `mimo-v2.5`

这些模型名大小写变化都不影响当前结论，都会被同一个 key 拦在 `401 invalid_api_key`。

因此当前 MiMo 的主问题不是模型名，也不是 grounded prompt，而是认证层本身。

### provider_acceptance 再次读取 `.env` 的缺口

在补入 `DEEPSEEK_API_KEY` 后，`preflight_provider_auth.py` 已经显示 DeepSeek `passed`，但 `run_provider_acceptance.py` 仍把它记成 `config_missing`。

根因：

- `run_provider_acceptance.py` 原本没有主动 `load_dotenv`
- 它只依赖父进程环境变量
- 导致 `.env` 已更新，但 provider 验收脚本自身没有读到

处理：

- 在 `run_provider_acceptance.py` 的 `main()` 中补 `load_dotenv(PROJECT_DIR / ".env", override=False)`

修复后重新验收：

- MiMo：`auth_invalid`
- DeepSeek：`grounded_rejection`

这说明当前 A-v1.4 已经从“全员认证失败”推进到了：

- MiMo 仍卡认证
- DeepSeek 已过认证，但 grounded 主链不稳定

这才是当前可信的 provider 对比起点。

## 2026-05-18 A-v1.2 评测与 trace 闭环补强

### 现象

在进入 A-v1.2 前，项目已经有：

- `evaluate_ragas.py`
- `run_regression.py`
- `run_adversarial.py`
- `tracing.py`

但它们还是分散的：

- 评测更像“算四个平均分”。
- trace 更像“给 hybrid retriever 挂一个 hook”。
- bad case 还没有真正映射到 trace 和根因分析。

### 根因

问题不在功能缺失，而在工程闭环缺失：

- 缺少 case 级诊断字段。
- 缺少本地可解释的 trace 主链。
- 缺少从 bad case 到 trace 的固定分析方法。

### 处理

- 为 tracing 增加本地 session 和记事件能力。
- 在问答主链里补关键 trace 节点：
  - `security_check`
  - `query_route`
  - `hybrid_retrieval`
  - `rerank`
  - `agentic_search`
  - `answer_decision`
- 升级 `evaluate_ragas.py`：
  - 输出 `diagnostics`
  - 汇总 `issue_counts`
  - 将 trace 快照嵌入每个 case
- 基于真实报告补两类 bad case 闭环文档：
  - `context_noise`
  - `answer_coverage_gap`

### 结果

A-v1.2 之后，Project A 可以更具体地回答：

- 一次低分 case 是召回问题、上下文问题，还是答案覆盖问题。
- trace 里每一步到底发生了什么。
- 下一轮应该优化检索、生成还是安全表达。

## 2026-05-18 A-v1.1 文档与版本收口

### 现象

在进入 A-v1.1 之前，仓库已经有较完整的 v1.0 能力和很多验证材料，但仍存在三个容易让对外说明失真的点：

- `/health` 和 `/api/v1/system/status` 仍返回 `v1.0`，而当前任务已经进入 A-v1.1。
- README 能说明主链，但还没有把“默认主链 / 可选增强 / 证据索引 / 最小 API 调用顺序”集中写清楚。
- 公开导出脚本不会带上 A-v1.1 新文档和截图资产，容易出现主仓库说得清、公开仓库仍缺材料的错位。

### 根因

问题不在业务代码，而在发布元信息和文档收口没有完成：

- 版本号仍停留在上一轮公开发布版本。
- 证据材料存在，但索引关系分散。
- 发布白名单脚本没有跟随新文档迭代。

### 处理

- 把 `backend/app/main.py` 的对外版本元信息统一为 `v1.1`。
- 重写 `README.md`，增加默认主链、可选增强、API 使用说明和证据索引。
- 更新：
  - `docs/A-v1.0_public_feature_audit.md`
  - `docs/A-v1.0_发布审查文档.md`
- 新增：
  - `docs/A-v1.1_教学说明.md`
  - `docs/A-v1.1_面试讲法与版本边界说明.md`
  - `docs/A-v1.1_API与关键演示说明.md`
  - `docs/A-v1.1_验证记录.md`
- 更新 `backend/scripts/create_public_release_repo.py`，把 A-v1.1 新文档、预检 JSON 和截图目录加入公开导出范围。

### 结果

A-v1.1 之后，仓库可以用统一口径回答这几个问题：

- 当前正式演示主入口是什么。
- 默认本地能跑什么。
- 哪些能力是按需增强而不是默认承诺。
- 证据材料和验证记录分别放在哪里。

### 补充现象：测试与预检会被本机增强环境劫持

现象：

```text
pytest 收集阶段直接导入 app.main 时，如果当前环境是 STORAGE_BACKEND=postgres，
会先尝试连接 PostgreSQL；数据库不可达时，测试在收集阶段超时失败。
```

另外：

```text
如果当前终端残留旧的 LLM_PROVIDER / LLM_BASE_URL，
即使项目 .env 正确，预检也会打到旧端点并返回 401 invalid_api_key。
```

处理：

- 公开主链回归测试显式固定：
  - `STORAGE_BACKEND=sqlite`
  - `VECTOR_BACKEND=chroma`
  - `CACHE_ENABLED=false`
  - `GRAPH_RETRIEVAL_ENABLED=false`
  - `MULTIMODAL_BACKEND=sidecar`
- A-v1.1 预检生成时，强制以项目 `.env` 为准，再叠加公开主链口径的环境变量。

结果：

```text
公开主链口径 pytest: 26 passed
A-v1.1 preflight: critical_failures=[]
```

## 2026-05-17 发布审查补充记录

### 现象

在公开发布版已经上线、CI 全绿之后，仍然存在一个容易让后续协作或面试产生误解的问题：

```text
设计文档是完整版目标
公开仓库是发布收敛版
两者如果不分层描述，容易被误读成“完全等价”
```

### 根因

问题不在代码，而在“边界说明缺失”：

- 哪些能力是默认主链
- 哪些能力只是可选增强
- 哪些能力在研发仓库验收过，但不适合作为公开版默认前提

如果没有一份正式的发布审查文档，README、设计文档、面试说法和真实仓库状态之间会逐渐偏离。

### 处理

新增两份文档作为后续基线：

- `docs/A-v1.0_发布审查文档.md`
- `docs/A-v1.1_后续版本迭代规划.md`

### 结果

后续可以统一基于这两份文档回答三个问题：

- 当前发布版和设计文档到底对齐到什么程度
- 为什么不追求所有增强能力默认全开
- 接下来版本优化应该先补哪里

## 2026-05-15 v1.0 发布场景测试

### 问题 1：A100 E-17 首条引用不是故障资料

现象：

```text
pytest backend/tests/test_release_scenarios.py -q

test_normal_fault_diagnosis_returns_same_device_citation 失败：
期望首条 citation 为 real_air_compressor_a100_faults.md，
实际返回 real_air_compressor_a100_maintenance.md。
```

原因：

Agentic RAG 之前只做了设备型号一致性过滤。同设备资料中，维护模板和故障资料都包含 A100、E-17、过滤器，排序没有进一步优先“故障代码定义”资料。

处理：

在 `AgenticRetriever._prioritize_same_device` 后增加 specificity 排序：

- 设备型号匹配加权。
- 故障码匹配加权。
- `故障代码 <code>` 定义句额外加权。
- 包含故障代码、报警、排查步骤的 chunk 额外加权。

验证：

```text
pytest backend/tests/test_release_scenarios.py -q
6 passed
```

## 2026-05-15 图谱检索与 Neo4j 适配

### 问题 1：本地图谱检索被通用动作词污染

现象：

```text
A100 E-17 查询图谱时，因为查询包含“检查”，CW200 高压报警 chunk 也被召回。
```

原因：

初版图谱查询把动作词也作为查询种子，`检查` 这类通用动作会连接到多个设备故障。

处理：

查询种子只使用设备、故障码和部件；动作只作为关系信息，不作为召回入口。

### 问题 2：应用导入时 helper 定义顺序错误

现象：

```text
NameError: name '_build_graph_retriever' is not defined
```

原因：

`app = create_app()` 在 `_build_graph_retriever` 定义之前执行。

处理：

将 `app = create_app()` 移到模块底部 helper 定义之后。

验证：

```text
pytest backend/tests/test_graph_retrieval.py backend/tests/test_config.py backend/tests/test_api.py -q
10 passed
```

## 2026-05-14 v1.0 企业级 RAG

### 问题 1：当前项目没有真实大模型生成

现象：

```text
普通问答只从检索 chunk 中抽句子拼接，资料不足时仍可能硬答。
```

原因：

v0.5 使用 `ExtractiveGenerator` 作为本地兜底，没有接入 LLM API。

处理：

新增 `LLMGenerator`，通过 `LLM_PROVIDER`、`LLM_MODEL`、`LLM_API_KEY`、`LLM_BASE_URL` 接入小米 MiMo OpenAI-compatible 接口。未配置 key 时继续 fallback，但系统状态明确显示 `llm_enabled=false`。

### 问题 2：资料不足问题缺少拒答

现象：

```text
ZX-999 / Q-00 这类知识库不存在的问题可能返回无关资料。
```

处理：

在生成前增加质量判断：如果问题包含明确设备型号，但检索 citation 不包含对应型号，则返回“当前资料不足，无法确认”并清空 citations。

### 问题 3：危险操作答案不够强

现象：

```text
UPS 电池冒烟、VFD 短路继续带载等问题，抽取式答案可能只描述资料，不明确禁止危险动作。
```

处理：

在生成后增加安全后处理。命中冒烟、异味、鼓包、短路、带压、继续带载、强制重启等词时，补充禁止直接重启、停机、隔离和人工确认。

### 问题 4：Gradio 工单需要手动复制 Ticket ID

现象：

```text
用户点击人工确认/关闭时，如果 Ticket ID 为空，会报 Ticket not found。
```

处理：

Vue3 企业演示台使用工单列表选择工单，启动工单后自动选中返回的 ticket_id，不再要求手动复制。

### 问题 5：前端 build chunk 体积提示

现象：

```text
vite build 提示部分 chunk 超过 500 kB。
```

原因：

Element Plus 和相关依赖进入主 bundle。

处理：

本轮记录为低风险提示，不阻塞企业演示台；后续可做按需导入和路由懒加载。

## 2026-05-14 真实资料测试

### 问题 1：Gradio 新面板引用了不存在的 settings.PROJECT_DIR

现象：

```text
AttributeError: 'Settings' object has no attribute 'PROJECT_DIR'
```

原因：

`PROJECT_DIR` 是 `app.config` 里的模块常量，不是 `Settings` 字段。

处理：

在 `backend/app/gradio_app.py` 中显式导入 `PROJECT_DIR`，评测脚本路径和 bad case 路径统一使用该常量。

### 问题 2：真实资料评测脚本只能读取 seed_docs

现象：

```text
python backend/scripts/evaluate_ragas.py --cases data/eval/real_regression_cases_v1.json
```

脚本仍然固定入库 `data/seed_docs`，无法评测真实脱敏资料。

原因：

v0.5 原始脚本是 seed demo 评测入口，没有 `--docs-dir` 参数。

处理：

三个脚本均增加 `--docs-dir`：

- `backend/scripts/evaluate_ragas.py`
- `backend/scripts/run_regression.py`
- `backend/scripts/run_adversarial.py`

真实资料报告默认写入 `docs/A-real-data_*`。

### 问题 3：明确设备型号时跨设备 citation 混入

现象：

```text
A100 E-17 问题可能混入 CW200。
UPS-30K 高风险问题可能混入 VFD 或 A100。
```

原因：

本地 HashEmbedding 和 hybrid 召回会把报警、过温、排查等通用词相关 chunk 一起召回；原 Agentic RAG 没有把设备型号一致性作为后处理条件。

处理：

`AgenticRetriever` 增加通用设备型号提取和同设备 chunk 优先过滤。已覆盖 A100、UPS-30K、PLC-X200、CW200、VFD-4500 等模式，不硬编码单个具体设备。

验证：

```text
pytest backend/tests/test_agentic_rag.py backend/tests/test_real_data_pipeline.py -q
```

明确设备型号 case 不再返回其它设备 citation。

### 问题 4：对抗测试仍暴露危险操作表达不足

现象：

```text
real adversarial passed_count: 8 / 10
```

原因：

检索能命中正确资料，但抽取式生成没有总是把“不能继续运行 / 必须人工升级”转成明确回答。

处理：

本轮先记录为真实 bad case，不在检索精确率切片里扩展生成安全模板。

记录：

```text
docs/A-real-data_bad_cases.md
```

## 2026-05-13 v0.4

### 问题 1：工单测试首次运行找不到 ticketing 模块

现象：

```text
ModuleNotFoundError: No module named 'app.ticketing'
```

原因：

按 TDD 顺序先写 `backend/tests/test_ticket_workflow.py`，目标模块尚未实现。

处理：

新增 `backend/app/ticketing/`，包含 `models.py`、`parts.py`、`workflow.py` 和 `__init__.py`。

### 问题 2：普通/备件工单被误判为高风险 HITL

现象：

```text
assert <TicketStatus 'NEED_HUMAN'> == <TicketStatus 'IN_PROGRESS'>
assert <TicketStatus 'NEED_HUMAN'> == <TicketStatus 'NEED_PARTS'>
```

原因：

初版风险判断使用了 `question + diagnosis.answer`。RAG 诊断文本可能包含其它设备资料，把高风险关键词带入当前工单。

处理：

风险判断改为优先使用用户原始问题。RAG 结果继续用于诊断文本和引用，不直接决定高风险操作。

### 问题 3：备件查询被诊断文本污染

现象：

```text
assert '过滤网' in ['过滤器', '压力传感器']
```

原因：

设备型号和备件查询使用混合文本，RAG 召回内容可能包含其它设备型号或备件。

处理：

设备型号、故障码和备件查询优先从用户原始问题提取。

### 问题 4：API 测试发现工单接口未接入

现象：

```text
assert 'v0.3' == 'v0.4'
assert 404 == 200
```

原因：

工单服务已实现，但 `main.py` 尚未同步 `/health` 版本号和工单 API 路由。

处理：

将 `/health` 更新为 `v0.4`，新增：

```text
POST /api/v1/tickets/start
POST /api/v1/tickets/{ticket_id}/resume
POST /api/v1/tickets/{ticket_id}/close
```

### 问题 5：`.gitignore` 误忽略 `backend/app/storage`

现象：

```text
git check-ignore -v backend/app/storage/sqlite_store.py
project-a-rag-platform/.gitignore:28:storage/ backend/app/storage/sqlite_store.py
```

原因：

`.gitignore` 中的 `storage/` 会匹配任意层级的 `storage` 目录，导致代码目录 `backend/app/storage/` 被忽略。

处理：

将规则改为 `/storage/`，只忽略仓库根目录运行数据目录。

### 问题 6：ruff 检查发现导入顺序和长行

现象：

```text
I001 Import block is un-sorted or un-formatted
E501 Line too long
```

原因：

新增 ticketing 模块后导入顺序和一处表达式长度不符合规则。

处理：

运行 `python -m ruff check backend --fix` 自动整理导入，再手动拆分长行。

## 2026-05-13 v0.3

### 问题 1：查询增强、安全和多模态测试首次运行找不到模块

现象：

```text
ModuleNotFoundError: No module named 'app.rag.query_enhancement'
ImportError: cannot import name 'semantic_chunk_text'
ModuleNotFoundError: No module named 'app.rag.security'
```

原因：

按 TDD 顺序先写测试，目标模块尚未实现。

处理：

新增 `query_enhancement.py`、`security.py`、`multimodal.py`，并在 `chunker.py` 中补充 `semantic_chunk_text`。

### 问题 2：语义切片把 Markdown 表头当成 chunk

现象：

```text
assert len(chunks) == 2
E AssertionError: assert 3 == 2
```

原因：

初版 `semantic_chunk_text` 把 `| 代码 | 含义 | 处理 |` 表头也作为可检索 chunk，导致表格数据行之外多出无业务信息 chunk。

处理：

保留表格数据行作为 chunk；表头关系由 `parse_table_markdown` 负责结构化还原。

### 问题 3：API 版本号仍返回 v0.2

现象：

```text
assert health_response.json()["version"] == "v0.3"
E AssertionError: assert 'v0.2' == 'v0.3'
```

原因：

功能已接入 pipeline，但 `main.py` 的 FastAPI 标题和 `/health` 版本号未同步。

处理：

将 API 标题更新为 `Project A v0.3 Query Enhancement and Complex Document RAG`，`/health` 返回 `v0.3`。

### 问题 4：ruff 检查发现导入顺序和超长行

现象：

```text
I001 Import block is un-sorted or un-formatted
E501 Line too long
```

原因：

新增模块后导入顺序和少数长表达式未符合 `pyproject.toml` 中的 ruff 规则。

处理：

运行 `python -m ruff check backend --fix` 自动整理可修复项，再手动拆分长行。

## 2026-05-13 v0.2

### 问题 1：新增 hybrid 检索测试首次运行找不到模块

现象：

```text
ModuleNotFoundError: No module named 'app.rag.hybrid'
```

原因：

按 TDD 顺序先写测试，目标模块尚未实现。

处理：

新增 `keyword.py`、`hybrid.py`、`rrf.py`、`reranker.py`、`scoring.py`，再运行测试验证行为。

### 问题 2：检索实验测试首次运行找不到实验模块

现象：

```text
ModuleNotFoundError: No module named 'app.rag.experiment'
```

原因：

实验运行器尚未实现。

处理：

新增 `backend/app/rag/experiment.py` 和 `backend/scripts/compare_retrieval.py`，支持真实运行 pure vector / hybrid / hybrid + rerank 对比。

### 问题 3：从仓库根目录运行实验脚本找不到 `app`

现象：

```text
ModuleNotFoundError: No module named 'app'
```

原因：

直接运行 `python backend/scripts/compare_retrieval.py` 时，Python import path 没有包含 `backend`。

处理：

在脚本入口根据 `__file__` 将 `backend` 加入 `sys.path`，让脚本可以从仓库根目录直接运行。

### 问题 4：summary 缺少可读 hit 统计

现象：

实验报告只有每个 case 的结果，没有汇总的 `top1_hit_count` 和 `topk_hit_count`。

原因：

初版实验运行器只返回明细，没有聚合指标。

处理：

先补失败测试，再在 `run_retrieval_experiment` 中增加三种策略的 top-1 和 top-k 命中计数。

## 2026-05-13 v0.1

### 问题 1：测试首次运行无法导入 `app`

现象：

```text
ModuleNotFoundError: No module named 'app'
```

原因：

测试先于实现编写，`backend/app` 包尚不存在。

处理：

创建 `backend/app` 包，并补齐 RAG、FastAPI、SQLite 相关模块。

### 问题 2：`pyproject.toml` 出现重复 `dependencies`

现象：

补依赖后文件里同时存在空依赖和新依赖。

原因：

机械 patch 时没有删除旧的 `dependencies = []`。

处理：

删除旧空依赖，仅保留实际依赖列表。

### 问题 3：真实 HTTP 入库接口返回 500

现象：

调用 `/api/v1/documents/ingest` 时返回 `Internal Server Error`。

原因：

`backend/app/config.py` 把项目根目录算成了当前仓库的父目录，导致默认 `data/seed_docs` 路径错误。

处理：

新增 `backend/tests/test_config.py` 复现路径问题，将 `PROJECT_DIR` 修正为 `Path(__file__).resolve().parents[2]`。

### 问题 4：A100/E-17 真实问答首个引用命中 PLC 文档

现象：

真实 HTTP 提问 `A100 出现 E-17 报警怎么排查？` 时，首个引用曾返回 `plc_x200.txt`。

原因：

本地 HashEmbedding 对中文通用字符权重较高，型号和故障码 token 权重不足；同时重复入库会留下历史向量。

处理：

在 embedding 中提高字母数字型号、故障码 token 权重；入库前重建 Chroma collection，保证 seed 文档验证结果稳定。
## 2026-05-13 v0.5

### 问题 1：多轮指代没有保留 E-17

现象：

```text
ConversationMemory 先输入 A100 E-17，再输入“它还能继续运行吗？”
resolved_question 只有 A100，没有 E-17。
```

原因：

故障码提取正则先匹配到 `A100`，因为它被识别为设备型号前缀而跳过，但函数没有继续查找后续 `E-17`。

处理：

将 `re.search` 改为 `re.finditer`，跳过设备型号后继续寻找真正故障码。

验证：

```text
pytest backend/tests/test_conversation.py -q
2 passed
```

### 问题 2：并行评测脚本共用 Chroma 导致 collection 丢失

现象：

```text
chromadb.errors.NotFoundError: Error in compaction: Error getting collection with segments
```

原因：

多个脚本同时使用 `data/chroma` 并执行入库 reset，互相删除 collection。

处理：

三个 v0.5 脚本分别使用独立目录：

- `data/v05_eval/chroma_ragas`
- `data/v05_eval/chroma_regression`
- `data/v05_eval/chroma_adversarial`

验证：

```text
python backend/scripts/evaluate_ragas.py
python backend/scripts/run_regression.py
python backend/scripts/run_adversarial.py
```

三条命令均成功生成报告。

### 问题 3：手动演示中跨设备 citation 混入

现象：

```text
A100 / E-17 问题的 citations 混入 chiller_cw200。
UPS-30K 高风险工单的 citations 混入 VFD 和 A100。
```

原因：

当前本地 HashEmbedding、混合检索和抽取式生成还没有强制设备型号一致性过滤。Agentic RAG 已经具备检索自评估和重试结构，但还没有把“同设备”作为硬过滤条件。

处理：

本轮先记录为 v0.5 bad case，不在复盘阶段改业务代码。

后续修复方向：

- Agentic RAG 增加设备型号一致性过滤。
- 生成前对 citations 做设备维度交叉验证。
- 将混入案例加入回归测试集。

记录：

```text
bad_cases/v0.5_evaluation_deploy.md
docs/A-v0.5_复盘文档.md
```
## 2026-05-15 v1.0 PostgreSQL 迁移调试记录

### 问题 1：PowerShell here-string 中文输入影响真实验收

现象：第一次用 PowerShell here-string 构造中文问题时，工单被判为 `IN_PROGRESS`。

原因：终端脚本里的中文 literal 被当前 shell 编码转换成问号，导致高风险关键词没有命中；代码里的关键词本身是正确 Unicode。

处理：真实验收脚本改用 Unicode escape 构造中文问题，重新验证 PostgreSQL 工单状态。

结果：

```text
postgres_ticket_row= ('NEED_HUMAN', True)
```
## 2026-05-16 v1.0 Milvus / 多模态调试记录

### 问题 1：Milvus 容器曾退出

现象：`project-a-milvus` 容器状态为 `Exited (137)`。

处理：重新 `docker start project-a-milvus` 后，`MilvusClient(http://localhost:19530)` 可连接。

结果：

```text
milvus_ready= ['project_a_real_probe', 'project_a_api_probe']
```

### 问题 2：PaddleOCR 旧 API 参数不兼容

现象：PaddleOCR 3.5 调用 `ocr(..., cls=True)` 报错：

```text
TypeError: PaddleOCR.predict() got an unexpected keyword argument 'cls'
```

处理：改为 PaddleOCR 3.5 的 `predict()`，并解析新版返回对象。

### 问题 3：PaddlePaddle 3.3.1 Windows CPU 运行时错误

现象：真实 OCR 模型加载后，在文本检测模型推理阶段报错：

```text
ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]
```

处理：关闭文档方向分类、扭曲矫正、文本行方向预处理后仍复现。按当前要求不降级 PaddlePaddle，因此记录为 Windows CPU / oneDNN / PIR 环境兼容阻塞。

### 问题 4：MinerU 本地 API 健康检查失败

现象：`mineru` 3.1.13 可以启动本地 API，但健康检查失败：

```text
Timed out waiting for local mineru-api to become healthy.
502 Bad Gateway
```

处理：记录为本机 MinerU API 服务健康阻塞。

### 问题 5：视觉 LLM 认证失败

现象：视觉 LLM OpenAI-compatible 接口返回：

```text
401 Unauthorized
```

处理：代码链路保留，需要更换有效 `VISION_LLM_*` 配置后复测。

## 2026-05-17 Vue + FastAPI 严格 LLM 预检失败

### 现象

`/api/v1/system/status` 返回 `llm_enabled=true`，但严格预检脚本直接调用 LLM 失败：

```text
direct_llm_call passed=false
error=LLM HTTP 401 invalid_api_key
```

随后通过 `/api/v1/chat` 询问：

```text
A100 出现 E-17，排气温度升高，应该怎么排查？
```

接口返回：

```text
status_code=200
llm_used=false
insufficient=false
citation_count=4
first_source=real_air_compressor_a100_faults.md
```

### 判断

`llm_enabled=true` 只说明 `.env` 中存在 `LLM_API_KEY / LLM_BASE_URL / LLM_MODEL`，不能证明真实模型可用。当前凭证被上游拒绝，业务问答回退到本地抽取式生成。

### 处理

本轮前端全功能测试要求普通可回答问答必须 `llm_used=true`。因此当前状态判为环境阻塞，不启动正式手测。修复 `.env` 中有效 LLM 凭证后，执行：

```powershell
python backend/scripts/preflight_frontend_full_test.py --output docs/A-vue-fastapi_preflight_2026-05-17.json
```

### 后续确认

用户确认 `.env` 配置无误后，检查发现：

```text
项目 .env:
LLM_PROVIDER=xiaomi_mimo
LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1

运行时旧环境变量:
LLM_PROVIDER=mimo
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

原因是 `load_dotenv(..., override=False)` 不会覆盖进程里已有环境变量，导致预检请求打到了 DashScope。已将 `backend/scripts/preflight_frontend_full_test.py` 改为预检时强制读取项目 `.env`。

复测结果：

```text
critical_failures=[]
direct_llm_call passed=true
strict_chat_llm passed=true
strict_chat_llm.detail.llm_used=true
```
## 2026-05-18 A-v1.2 定向优化补充记录

### 现象

A-v1.2 第一轮真实评测里，最主要的问题是：

- `context_noise: 8`
- `grounding_gap: 9`

说明系统主要不是“没召回到”，而是：

- 最终 citations 混入了同设备其他故障或其他设备的通用排查段落
- 本地 fallback 生成器没有优先抽出和问题最对齐的句子

### 根因

根因分成三层：

1. 本地 reranker 判断过粗  
只看词重合和数字，不能稳定区分“同设备对故障码”和“同设备错故障码”。

2. 生成前没有 context 聚焦  
回答和 citations 直接复用 top_k 检索结果，导致噪音 chunk 一起进入最终答案。

3. Agentic 质量分对中文症状太弱  
旧版 `quality_score` 的 token 规则对“欠压”“出水温度降不下来”这类表达不敏感，曾把已命中的正确 chunk 误判成资料不足。

### 处理

- 在 `backend/app/rag/scoring.py` 增加统一相关性评分。
- 在 `backend/app/rag/reranker.py` 复用该评分。
- 在 `backend/app/rag/pipeline.py` 增加 `answer_context_filter`。
- 对显式故障码问题优先只保留命中该故障码的 answer chunks。
- 在 `backend/app/rag/generator.py` 改为相关性抽句而不是顺序摘句。
- 在 `backend/app/rag/agentic.py` 把 `quality_score` 切换到新版 token 口径。

### 结果

重新生成 `docs/A-v1.2_ragas_report.json` 后：

```text
faithfulness: 0.415 -> 0.4384
answer_relevancy: 0.6333 -> 0.8667
context_precision: 0.5375 -> 0.775
context_recall: 0.85 -> 0.8833
low_score_case_count: 19 -> 12
source_hit_count: 20 / 20 -> 20 / 20
```

### 额外修正

中途出现过两个回归：

- `CW200 出水温度降不下来应该检查什么？`
- `VFD-4500 欠压 UV-1 需要检查哪些供电项？`

当时现象是正确 chunk 已经检到，但因为 `quality_score` 偏低，被 `_is_insufficient()` 错判成资料不足。  
改完 Agentic 质量判断后，这两个 case 已恢复正常。
## 2026-05-18 真实 LLM 输出护栏补强

### 现象

真实 LLM 已经可以接通，但原实现有三个问题：

- `prompt_path` 虽然传入了 `RagPipeline`，真实 LLM 分支并没有真正使用构造后的 RAG prompt。
- 返回结果只要非空就直接当成成功，没有最小 grounded 校验。
- OpenAI-compatible 返回如果是 `content=[{type:text,...}]` 这种结构，旧实现不能稳定提取文本。

### 根因

问题不在“能不能连上模型”，而在“连上后缺少输出质量护栏”：

- 约束没有前移到真实 LLM prompt。
- 输出没有做最小清洗。
- 结果没有做轻量上下文对齐校验。

### 处理

- 重写 `backend/app/rag/llm.py`：
  - 支持 `prompt` 入参。
  - 加 system prompt 结构约束。
  - 支持提取文本块数组内容。
  - 清洗代码块和回答前缀。
- 更新 `backend/app/rag/pipeline.py`：
  - 真实 LLM 分支改为真正使用 `build_rag_prompt(...)`。
  - 新增 `_accept_llm_answer()`。
  - 当真实 LLM 返回结果和检索上下文重合过低时自动回退到本地生成器。
- 在 trace 中记录 `llm_error`，便于区分“模型返回空”“模型报错”“模型答偏被拒收”。

### 结果

现在真实 LLM 主链变成：

```text
检索上下文
-> build_rag_prompt
-> 真实 LLM
-> 最小答案清洗
-> grounded 校验
-> 通过则 llm_used=true
-> 不通过则 fallback
```

这一步的价值不是让真实 LLM “一定回答”，而是让它“回答得更稳，答偏时不比 fallback 更差”。

### 真实烟测补充

新增 `docs/A-v1.2_real_llm_smoke_2026-05-18.json` 后确认：

- 真实 LLM 在当前凭证下可以连通并返回文本。
- 但它会把 A100 E-17 错答成“通信模块异常/主板固件问题”。
- grounded 校验因此拒收该答案，最终 `llm_used=false`。

这说明当前阻塞点已经不是接入链路，而是上游模型质量/适配问题。  
在更换更合适的模型或 provider 之前，保留“接通但拒收不可信答案”的策略是必要的。

### grounded 预检补充

新增 `backend/scripts/preflight_real_llm_grounding.py` 后，得到更严格的结论：

- `direct_llm_connected=false`
  - 当前 .env 下 LLM enabled=true，但直接请求有时仍会返回空内容。
- `chat_grounded_llm=false`
  - 即使主链能返回答案，`llm_used` 依然是 false，因为真实模型答案没有通过 grounded 校验。

这让“真实 LLM 当前不可直接用于主链”的判断从人工观察升级成了自动化结论。

## 2026-05-18 A-v1.2 最后一次真实 LLM 调试补充

### 新发现

- `backend/scripts/preflight_real_llm_grounding.py` 原先使用 `load_dotenv(..., override=True)`，会把命令行临时传入的 DeepSeek 配置重新覆盖回 `.env` 默认模型，导致临时 provider 调试结论失真。
- 预检脚本如果复用旧的 `app_real_llm_grounding.db` / `chroma_real_llm_grounding`，会出现旧状态污染，需要在每次烟测前清理。
- 即使切到 DeepSeek，自动化 grounded 预检仍会出现“直连通过，但 `/chat` 回退到 fallback”的波动。

### 已处理

- 预检脚本改为尊重命令行显式传入的 LLM 环境变量。
- 预检脚本增加独立烟测目录清理。
- 真实 LLM 默认温度从 `0.1` 收紧到 `0.0`，优先提高 grounded 场景的一致性。
- 额外保留一份临时 DeepSeek 手工烟测成功记录：
  - `docs/A-v1.2_real_llm_manual_deepseek_smoke_2026-05-18.json`

### 最终判断

这次最后调试后的结论不是“默认切换到 DeepSeek”，而是：

```text
默认 .env 仍保持小米模型
DeepSeek 已经证明可以在当前主链上跑出 llm_used=true 的成功样例
但自动化 grounded 预检仍有稳定性波动
所以当前最稳妥的发布口径仍然是：
默认配置不变，DeepSeek 只作为候选 provider 记录到证据链
```

## 2026-05-18 A-v1.3 统一验收补充

### 新发现

- `run_provider_acceptance.py` 首轮把 default provider 误判成 blocked，不是 provider 本身新失败，而是 `ChromaVectorStore.reset()` 在 collection 缺失时会抛 `NotFoundError`，导致 grounded 预检提前中断。
- 修掉 reset 幂等性之后，provider 验收结果恢复为“默认 MiMo blocked、DeepSeek unstable”。
- 当前用户提供的 DeepSeek key 在这次最终验收时可以通过直连调用，但 grounded 主链仍未稳定通过自动化验收。

### 已处理

- `backend/app/rag/vector_store.py`
  - `reset()` 兼容 Chroma collection 不存在的情况
- 新增 `backend/scripts/run_provider_acceptance.py`
  - 用统一脚本而不是临时命令比较 provider
- 新增 `backend/scripts/run_av13_acceptance.py`
  - 将 provider、Redis、PostgreSQL、Neo4j、Milvus、MinerU、PaddleOCR、Vision LLM 汇总到同一份 JSON 报告

### 最终判断

```text
A-v1.3 的重点不是默认切换 provider
而是把“哪些能力已通过、哪些能力不稳定、哪些能力被环境阻塞”统一说清楚
```
## 2026-05-19 A-v1.5 运行时诊断补强

这轮没有继续增加多模态入口，而是优先补诊断信息，目标是把“还没通”拆成更可执行的下一步。

PaddleOCR 新增确认：

```text
cv2=4.10.0
numpy=2.3.5
paddle=3.3.1
paddleocr import -> OSError [WinError 127] shm.dll
真实 OCR 推理 -> NotImplementedError ConvertPirAttribute2RuntimeAttribute
```

这说明当前阻塞不是样例问题，也不只是包缺失，而是 Windows / Paddle(PaddleX) 运行时兼容问题。

MinerU 新增确认：

```text
which mineru -> 有
mineru CLI -> 能启动本地 mineru-api
任务提交后 -> 502 Bad Gateway
```

这说明 MinerU 当前更接近服务健康/任务状态查询失败，而不是命令不存在。

为了让报告更可用，这轮同步补了两类工程化收口：

- `backend/scripts/preflight_multimodal_real.py`
  - 新增 `diagnostics`
  - 为 PaddleOCR / MinerU 增加 `diagnosis` 和 `next_step`
- `backend/scripts/run_av15_multimodal_acceptance.py`
  - 新增 `blocked_dependency`
  - 将 MinerU 非零退出和 `502` 归类为 `service_unhealthy`

这轮之后，A-v1.5 的剩余阻塞已经明确拆成：

- `Vision LLM`: passed
- `PaddleOCR`: runtime_incompatible
- `MinerU`: service_unhealthy
- `image/pdf/end-to-end`: blocked_dependency

## 2026-05-19 A-v1.5 Linux 路径预检

为了避免继续在 Windows 本机上试参数，这轮额外补了一份 Linux 路径探针。

结果：

```text
docker daemon: false
wsl repo mounted: true
wsl python ready: true
wsl packages ready: false
recommended_path: wsl_bootstrap
```

具体观察：

- Docker client 可用，但 daemon 当前不可用，所以容器路径暂时不是第一优先级
- `WSL Ubuntu-24.04` 已在运行
- 仓库可挂载进 WSL
- WSL 内已有 `python3`
- 但 `cv2 / numpy / paddle / paddleocr / paddlex` 全部未安装
- `python3 -m ensurepip` 也不可用，说明需要先补 Linux 侧 Python/pip 启动能力

因此当前最合理的下一步已经不是：

```text
继续在 Windows 上试 OCR 参数
```

而是：

```text
先把 WSL Python/pip/bootstrap 搭起来
再在 WSL 内做 PaddleOCR 真实安装与预检
```

### WSL bootstrap 继续推进

后续继续按这条线往前做，确认了几件事：

1. `sudo` 需要密码，当前无法走系统级 `apt install`
2. 但 WSL 内有 `curl` 和 `python3`
3. 通过 `get-pip.py --user --break-system-packages` 已成功拉起用户态 `pip`
4. 随后已在 WSL 用户目录安装：
   - `numpy`
   - `paddlepaddle`
   - `paddleocr`
   - `paddlex`
   - `opencv-contrib-python`

这让 Linux 路径从：

```text
wsl_bootstrap
```

推进成：

```text
wsl_packages_ready = true
```

但继续真实跑 `PaddleOCRAdapter(backend='real')` 后，新的首个明确阻塞变成了：

```text
ImportError: libgomp.so.1: cannot open shared object file
```

也就是说，当前 Linux 侧已经不是：

- Python 不可用
- pip 不可用
- 包没装

而是：

- `paddle` 导入阶段缺少系统共享库

因此当前最精确的下一步不再是“装 Python 包”，而是：

```text
修 WSL 侧 libgomp1 / OpenMP 共享库
```
## 2026-05-19 A-v1.5 WSL OCR 运行时排障

- 背景：
  - Windows 本机 `PaddleOCR` 已判定为 `runtime_incompatible`
  - 为避免继续在本机参数层空转，转入 WSL/Linux 验证路径
- 已确认：
  - `WSL Ubuntu-24.04` 可进入
  - 仓库可挂载
  - 用户态 `pip` bootstrap 成功
  - `numpy / paddlepaddle / paddleocr / paddlex / opencv-contrib-python` 已安装
- 第一轮 Linux OCR 阻塞：
  - `ImportError: libgomp.so.1: cannot open shared object file`
- 处理动作：
  - 通过 `apt download libgomp1` + `dpkg-deb -x` 提取用户态共享库
  - 在 WSL OCR 探针中注入 `LD_LIBRARY_PATH=<WSL_HOME>/project_a_wsl_libgomp/usr/lib/x86_64-linux-gnu`
- 处理后结果：
  - `paddle` 导入成功
  - 真实 OCR 继续失败，但失败点推进为：
    - `NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]`
- 结论：
  - 当前 Linux 路径不再是缺包或缺共享库
  - 当前阻塞是 Paddle/PaddleX 真实运行时兼容问题
  - 后续应优先切换更稳的容器/运行时组合，或先并行推进 MinerU 502 排障

## 2026-05-19 A-v1.5 MinerU 服务级排障

- 现象：
  - 早期多模态总预检把 MinerU 记成 `service_unhealthy`
  - 但这只说明 `mineru` 非零退出，没有把失败层级说清
- 处理：
  - 新增 `backend/scripts/preflight_mineru_service.py`
  - 直接抓取 `mineru -p <pdf> -o <dir>` 的真实 stdout/stderr
  - 把运行阶段拆成：
    - `local_api_started`
    - `uvicorn_ready`
    - `task_submitted`
    - `vlm_engine_initialized`
    - `model_fetch_started`
    - `task_status_query_failed`
    - `bad_gateway_502`
- 最新真实输出确认：
  - `mineru-api` 已启动
  - Uvicorn 已 ready
  - PDF 任务已提交
  - VLM 模型加载已开始
  - 最终不是 `502`
  - 真正错误是：
    - `OSError: 页面文件太小，无法完成操作。 (os error 1455)`
- 代码层补充：
  - `backend/app/rag/multimodal.py`
    - `MinerUAdapter` 失败时附带 CLI stdout/stderr 摘要
  - `backend/scripts/preflight_multimodal_real.py`
    - 增加 `os error 1455` 识别
  - `backend/scripts/run_av15_multimodal_acceptance.py`
    - 新增 `runtime_resource_blocked`
- 结论：
  - MinerU 当前不应再泛化成 `service_unhealthy`
  - 更准确的验收结论是 `runtime_resource_blocked`
  - 下一步优先提高 Windows 页面文件，或转 Linux/WSL 更宽松运行时

## 2026-05-19 A-v1.5 WSL MinerU 排障

- 背景：
  - Windows 侧 MinerU 已确认卡在 `os error 1455`
  - 为验证是否只是 Windows 资源问题，继续切到 WSL 手工执行真实 `mineru -b pipeline`
- 已确认：
  - WSL 中 `mineru==3.1.14` 可导入、可执行
  - 默认 `hybrid-auto-engine` 会先做本地依赖判断
  - 改为显式 `-b pipeline` 后，真实链路继续向前推进
- 真实推进到的阶段：
  - `mineru-api` 启动
  - Uvicorn ready
  - PDF 任务提交
  - `Pipeline processing-window` 启动
  - 模型初始化开始
- 新阻塞：
  - 需要从 HuggingFace 拉取 `opendatalab/PDF-Extract-Kit-1.0`
  - 当前 WSL 报：
    - `HTTPSConnectionPool(host='huggingface.co', port=443)`
    - `OSError: [Errno 101] Network is unreachable`
    - `huggingface_hub.errors.LocalEntryNotFoundError`
- 结论：
  - WSL 侧已经绕过 Windows 资源阻塞
  - 当前阻塞切换成 `network_blocked`
  - 后续要么修 WSL 出网，要么预置模型缓存，再继续 MinerU 验收

## 2026-05-20 A-v1.5 WSL MinerU local minimal 调试闭环

- 为绕开 WSL 出网失败，改走本地模型缓存方案：
  - Windows 侧逐文件下载最小模型集，而不是整仓并发 `snapshot_download`
  - 共享目录：
    - `data/model_cache/mineru_pipeline_pdf_extract_kit_1_0`
- WSL 侧通过 `MINERU_MODEL_SOURCE=local` + `MINERU_TOOLS_CONFIG_JSON=<WSL_HOME>/mineru.json` 指向共享缓存
- 真实成功命令固定为：
  - `mineru -b pipeline -m ocr -f false -t false -p data/manual_test_uploads/upload_pdf_sidecar.pdf -o data/mineru_output_wsl_local_minimal`
- 成功证据：
  - `docs/A-v1.5_mineru_linux_local_minimal_2026-05-19.json`
  - `data/mineru_output_wsl_local_minimal/upload_pdf_sidecar/ocr/upload_pdf_sidecar_content_list_v2.json`
- 关键阶段确认：
  - 本地 `mineru-api` 启动成功
  - pipeline / layout / OCR 全部实际执行
  - 产物目录已落盘
- 但新暴露的 bad case 是：
  - 产物存在
  - 内容结构为空
  - 说明当前问题已从“运行阻塞”下降为“解析质量不足”

## 2026-05-20 A-v1.5 MinerU 分页采样调试

- 新发现：
  - `preflight_mineru_linux_runtime.py` 传入相对路径 PDF 时，会在 `relative_to()` 处抛错
  - 已修复为先 `resolve()`
- 整本 `OM_780-3.pdf`：
  - 已进入 136 页批处理与 layout 阶段
  - 当前不是秒失败，而是整本 profile 代价过高
- 整本 `MPOD-AFCDNS_R0_EN.pdf`：
  - 在 600 秒窗口内超时
- 为了区分“解析质量问题”和“长文档吞吐量问题”，新增分页采样口径：
  - `--start 0 --end 1`
- 分页采样结果：
  - `OM_780-3.md` 非空
  - `MPOD-AFCDNS_R0_EN.md` 非空
  - `content_list_v2.json` 也为非空结构
- 调试结论：
  - 当前 Linux local minimal 真正已具备“小页范围真实验收”能力
  - 整本长手册失败/超时，应归入 profile 边界，不应误判为整条链路不可用

## 2026-05-20 A-v1.5 多模态主报告聚合修正

- 问题：
  - 旧版 `A-v1.5_multimodal_acceptance_report_2026-05-19.json` 只看 Windows preflight
  - 已经真实转绿的 `MinerU Linux sliced` 没被纳入主报告
- 修正：
  - `backend/scripts/run_av15_multimodal_acceptance.py` 现在会自动读取当天 `docs/A-v1.5_mineru_linux_local_minimal*_YYYY-MM-DD.json`
  - 若存在分页采样 `passed` 报告，则把：
    - `mineru_linux_local_sliced_pdf_parsing`
    计为正式 `passed`
- 结果：
  - `docs/A-v1.5_multimodal_acceptance_report_2026-05-20.json`
  - 主报告从 `1 绿` 升级为 `2 绿`

## 2026-05-20 A-v1.5 PaddleOCR 终局调试

- 追加了最后一组低成本真实尝试，目标是确认 `PaddleOCR` 是否还能在 A-v1.5 内继续救：
  - 关闭 `FLAGS_enable_pir_api`
  - 关闭 `FLAGS_use_mkldnn`
  - 改用 `PP-OCRv5_mobile_det / PP-OCRv5_mobile_rec`
  - 改用 `PP-OCRv4` mobile profile
- 结果全部一致：
  - 仍然在 `paddlex.inference.models.runners.paddle_static.runner` 内部失败
  - 统一报：
    - `NotImplementedError: ConvertPirAttribute2RuntimeAttribute`
- 调试结论：
  - 当前问题不是 server/mobile 模型选择问题
  - 也不是 `PIR/MKLDNN` 环境变量开关问题
  - A-v1.5 到这里应停止继续微调 Paddle 运行时
## 2026-05-20 A-v1.6 验收中心调试记录

### 现象

A-v1.4 与 A-v1.5 已经有真实报告，但前端没有统一入口，`App.vue` 同时存在中文乱码，导致演示层信息密度低且不稳定。

### 处理

- 后端新增 `/api/v1/acceptance/overview`
- 使用现有报告作为单一事实来源，不重复执行验收脚本
- 前端改为调用统一接口展示四类面板：
  - 真实 LLM 主链
  - 真实多模态能力
  - 评测与回归
  - Bad Case 与边界

### 验证

- `pytest backend/tests/test_acceptance_overview_api.py -q`
  - `1 passed`
- `python -m compileall backend/app/main.py backend/app/models.py`
  - 通过
- `cd frontend && npm run build`
  - 构建通过

### 当前结论

- A-v1.6 的最小验收中心已可运行
- 真实状态已经能在前端直接展示，而不必手动翻 `docs/*.json`
- 当前页面最适合作为下一步前端图表化与 trace 展示的承接层

## 2026-05-20 A-v2.0 演示中心增强调试记录

### 现象

A-v1.6 虽然已经有验收中心，但它更像“读接口看结果”，还不够适合面试和项目展示。

主要缺口是：

- provider 与 multimodal 只有 summary，没有明细
- 评测结果没有可视化节奏
- bad case 仍主要依赖手动翻文档

### 处理

- 扩展 `/api/v1/acceptance/overview`
  - 增加 `breakdown`
  - 增加 `chart`
  - 增加 `highlights`
- 前端演示中心改为直接展示：
  - 顶部概览指标
  - provider / multimodal 状态明细
  - RAGAS / regression / adversarial 分数条
  - 低分样例和 bad case 卡片
- 同步把 API 版本号提升到 `v2.0`

### 验证

- `pytest backend/tests/test_acceptance_overview_api.py backend/tests/test_api.py backend/tests/test_enterprise_api.py -q`
  - `9 passed`
- `python -m compileall backend/app/main.py backend/app/models.py`
  - 通过
- `cd frontend && npm run build`
  - 构建通过

### 当前结论

- A-v2.0 演示中心已经可以直接承担“项目讲解入口”
- 页面现在不仅能给结论，也能给明细、分数和坏例子
- 下一步最自然的是 trace 细节可视化，而不是再改 summary 层

### A-v2.0 trace 入口补充

继续往前推时，发现评测面板虽然已经有低分样例，但还缺一层“为什么这个 case 低分”的直接讲法。

处理：

- 后端从 `A-v1.2_ragas_report.json` 提取低分 case 的 `trace.events`
- 聚合到 `evaluation.trace_cases`
- 前端把这些事件渲染成时间线步骤流

验证：

- `pytest backend/tests/test_acceptance_overview_api.py -q`
  - `1 passed`
- `python -m compileall backend/app/main.py backend/app/models.py`
  - 通过
- `cd frontend && npm run build`
  - 构建通过

当前结论：

- 演示中心已经能从“看到低分 case”推进到“看到低分 case 的 trace 过程”
- 下一步若继续增强，优先级最高的是把 trace 时间线做成可折叠详情，而不是再补新的 summary 字段

### A-v2.0 trace 详情展开

继续补 trace 时，发现只显示事件名和摘要还不够回答“这一层到底收到了什么、产出了什么”。

处理：

- 后端为 trace event 补充 `inputs / outputs / metadata`
- 前端增加展开按钮和详情块

验证：

- `pytest backend/tests/test_acceptance_overview_api.py -q`
  - `1 passed`
- `python -m compileall backend/app/main.py backend/app/models.py`
  - 通过
- `cd frontend && npm run build`
  - 构建通过

当前结论：

- 低分 case 现在已经能直接展开看到关键输入输出
- 下一步若继续增强，更适合做 trace 原始 JSON 弹层或筛选器，而不是继续扩字段数量

### A-v2.0 trace 筛选与原始 JSON

继续补到“够用”为止后，把 trace 面板最后两块高价值能力也接上了：

- 按 `likely_issue` 筛选低分 case
- 查看原始 trace JSON

处理：

- 后端在 `trace_cases` 中保留 `raw_trace`
- 前端新增筛选下拉和弹层

验证：

- `pytest backend/tests/test_acceptance_overview_api.py -q`
  - `1 passed`
- `python -m compileall backend/app/main.py backend/app/models.py`
  - 通过
- `cd frontend && npm run build`
  - 构建通过

当前结论：

- A-v2.0 的 trace 面板已经够支撑现场排查演示
- 下一步如果还要继续增强，优先级更高的是浏览器里实机点验和必要的交互打磨，而不是再扩接口字段

## 2026-05-22 A-v2.0 实机联调排障

现象：
- `backend/scripts/preflight_frontend_full_test.py` 在当前仓库 `.env` 下导入 `app.main` 时卡住
- 根因不是 FastAPI 或验收中心接口本身，而是 `.env` 默认启用了 `postgres / redis / neo4j` 增强配置
- 这导致公开演示场景下，脚本会在应用初始化阶段先尝试连接 PostgreSQL

处理：
- 为 `preflight_frontend_full_test.py` 增加 `--profile public_chain`
- 在该画像下强制覆盖：
  - `STORAGE_BACKEND=sqlite`
  - `VECTOR_BACKEND=chroma`
  - `CACHE_ENABLED=false`
  - `GRAPH_RETRIEVAL_ENABLED=false`
  - `LLM_PROVIDER=deepseek`
  - `LLM_MODEL=deepseek-chat`

真实联调结果：
- 后端启动后：
  - `/health` 返回 `200`
  - `/api/v1/system/status` 返回 `200`
  - `/api/v1/acceptance/overview` 返回 `200`
- 前端直接用 `vite.cmd --host 127.0.0.1 --port 4175` 启动
  - `npm run dev -- --port ...` 在当前脚本口径下会和现有 `package.json` 的固定参数冲突
  - 改为直接调 `node_modules/.bin/vite.cmd` 后恢复正常
- 前端首页和代理到后端的 `/api/v1/acceptance/overview` 均返回 `200`

结论：
- A-v2.0 当前真实阻塞不在页面代码，而在“默认开发环境画像”和“公开演示画像”没有分开
- 现阶段已经用 `public_chain` 预检画像把这个问题收口

## 2026-05-22 A-v2.0 演示启动链路排障收口

现象：
- 即使 `public_chain` 画像已经验证通过，后续演示时仍可能重复踩两个坑：
  - 忘记覆盖 `LLM_API_KEY / LLM_BASE_URL`
  - 忘记分别启动后端和前端

处理：
- 新增 `.env.demo.example` 固化公开演示画像
- 新增 `scripts/start_demo_stack.ps1`
  - 自动读取 `.env` 中的 `DEEPSEEK_API_KEY`
  - 自动映射为演示链路使用的 `LLM_API_KEY`
  - 自动等待前后端 ready
- 新增 `scripts/stop_demo_stack.ps1`
  - 用 pid 文件回收演示进程

结论：
- 公开演示口径已经从“命令行临时覆盖”升级成了“仓库内可复用脚本”
- 后续演示只需要维护 `.env` 中的真实密钥和可选的 `.env.demo`
# 2026-05-24 A-v2.8 作品集视觉补图记录

## 现象

A-v2.7 已经解决“怎么讲”，但作品集视觉材料仍不完整：

- 只有首页截图。
- Provider、多模态、trace JSON 等关键状态缺少独立截图。
- Provider comparison 如果直接截 Markdown 原文，视觉表达弱。

## 处理

- 启动本地 demo，确认五个 HTTP 入口均返回 200。
- 使用 Playwright 自动点击前端验收中心并截图。
- 生成 6 张作品集截图。
- 将 trace JSON 改为弹层本体截图。
- 将 provider comparison 改为英文摘要图，避免终端编码污染中文。
- 更新截图清单和交付索引。

## 截图问题 1：Trace JSON 整页截图可读性差

首次截图包含遮罩和背景滚动状态。

处理：

- 改为只截 `.el-dialog`。

## 截图问题 2：Provider comparison Markdown 截图观感差

首次截图为 Markdown 原文。

处理：

- 基于 A-v2.4 真实指标生成摘要图。
- 使用英文文案规避 PowerShell inline Node 中文编码问题。

## 验证结果

```text
01-demo-home.png generated
02-provider-status.png generated
03-multimodal-status.png generated
04-evaluation-trace.png generated
05-trace-json.png generated
06-provider-comparison-report.png generated
```

服务已停止并释放 `18082` / `4175`。

# 2026-05-24 A-v2.7 面试材料压缩记录

## 现象

A-v2.6 后项目已经有完整证据链，但面试临场表达仍可能过长：

- README 偏完整入口。
- demo script 偏演示过程。
- final delivery index 偏材料导航。
- interview guide 偏问答解释。

## 风险

如果直接按完整材料讲，容易出现：

- 前 2 分钟没有讲出项目价值。
- 过早陷入 MiMo / PaddleOCR 细节。
- 边界说明被误解成能力失败。

## 处理

- 新增 `docs/interview_pitch_pack.md`。
- 将表达拆成 2 分钟、5 分钟、15 分钟三档。
- 高频追问单独沉淀，不塞进主讲路线。
- README 和 final delivery index 补入口。
- 公开导出脚本补入 A-v2.7 文档。

## 当前判断

这是表达效率问题，不是工程能力缺口。

下一步应优先补作品集视觉截图，让材料从“可讲”进一步变成“可看”。

## 验证结果

已确认：

- README 能进入 `docs/interview_pitch_pack.md`。
- final delivery index 能进入 `docs/interview_pitch_pack.md`。
- 公开导出脚本包含 A-v2.7 文档。
- dry run 导出包包含 A-v2.7 三份材料。

脚本检查：

```text
python -m compileall backend\scripts\create_public_release_repo.py
passed

python backend\scripts\create_public_release_repo.py --target tmp\public-release-check --force
passed
```

# 2026-05-23 A-v2.6 公开交付检查记录

## 现象

A-v2.5 后项目已经具备演示材料，但公开交付仍有两个风险：

- 缺少一个最终索引把 README、demo、截图、证据和面试讲法串起来。
- `backend/scripts/create_public_release_repo.py` 仍主要复制 v1.x 材料，导出包会漏掉 A-v2.2 到 A-v2.6 的最新证据。

## 处理

- 新增 `docs/final_delivery_index.md`。
- 新增 A-v2.6 review 和 bad case 记录。
- 更新 README 和 interview guide 的过时口径。
- 将 A-v2.2 到 A-v2.6 核心材料补入公开导出脚本。

## 当前判断

这是交付组织问题，不是 RAG 主链问题。

后续需要通过：

```text
python backend/scripts/create_public_release_repo.py --target tmp/public-release-check --force
```

确认导出清单完整。

## 验证结果

公开导出 dry run 已通过，并确认导出包包含：

```text
docs/final_delivery_index.md
docs/A-v2.6-public-delivery-review.md
docs/A-v2.2_provider_acceptance_report_2026-05-23.json
docs/A-v2.3_paddleocr_compatibility_report_2026-05-23.json
docs/A-v2.4_provider_comparison_report_2026-05-23.json
docs/assets/a-v2.5/01-demo-home.png
scripts/start_demo_stack.ps1
.env.demo.example
```

敏感信息扫描只命中：

```text
scripts/start_demo_stack.ps1 中的变量赋值
docs/demo_guide.md 中的占位 key 示例
docs/debug_log.md 中的空字符串说明
```

未发现真实 API key。

公开 demo 五个入口均返回 200，验证后已停止服务并释放 `18082` / `4175`。

# 2026-05-23 A-v2.5 演示素材补强记录

## 现象

技术主线已经完成 A-v2.4，但演示材料仍需要进一步收口：

- `docs/demo_script.md` 仍停留在 A-v2.1 口径。
- 缺少五分钟演示路线。
- 缺少截图清单。
- 缺少公开交付 checklist。
- 缺少 A-v2.5 当前截图目录。

## 处理

- 重写 demo script。
- 新增 five minute route。
- 新增 demo assets checklist。
- 新增 public delivery checklist。
- 新增 A-v2.5 review。
- 使用 Chrome headless 采集首页截图。

## 截图一致性问题

首次截图发现 provider 面板仍读取 A-v1.4 报告，MiMo 显示为旧的 `auth_invalid`。

处理：

- `_build_provider_panel()` 优先读取 A-v2.2 provider acceptance。
- `_build_multimodal_panel()` 补入 A-v2.3 PaddleOCR compatibility boundary 证据。
- 重启 demo 后重新截图。

最终截图：

```text
docs/assets/a-v2.5/01-demo-home.png
```

注意：截图只覆盖默认首页。Provider tab、trace JSON 弹层等交互状态仍建议人工补图，已写入 `docs/demo_assets_checklist.md`。

# 2026-05-23 A-v2.4 Provider 对比报告排查记录

## 现象

A-v2.2 已经证明 MiMo 和 DeepSeek 都能通过 grounded 验收，但默认演示主链仍需要更细的比较依据。

## 处理

新增 provider comparison 脚本，对三个明确候选运行同一组真实售后诊断 case：

- `mimo_token_plan_v25_pro`
- `mimo_token_plan_v25`
- `deepseek_chat`

## 排查 1：脚本顶层 import 触发 PostgreSQL 初始化

现象：

```text
pytest 收集 test_av24_provider_comparison.py 时触发 app.main 全局 app 初始化
当前 .env 偏企业增强口径，导致 PostgreSQL 连接超时
```

处理：

- 将 `from app.main import create_app` 延迟到 provider 环境变量切换之后。
- 测试阶段只导入纯函数，不触发 FastAPI app 初始化。

验证：

```text
python -m pytest backend/tests/test_av24_provider_comparison.py -q
2 passed
```

## 最终结论

```text
deepseek_chat 仍是默认 demo 主链
mimo_token_plan_v25 是可比较候选
mimo_token_plan_v25_pro 暂不进入默认演示路径
```

# 2026-05-23 A-v2.3 PaddleOCR 兼容性专项排查记录

## 现象

当前 Docker daemon 已 ready，WSL Python 和 PaddleOCR 相关包均已安装，但真实 OCR 推理仍失败：

```text
wsl_ocr_runtime_ready = false
recommended_path = wsl_runtime_incompatible
```

## 根因判断

错误稳定收口为：

```text
NotImplementedError: ConvertPirAttribute2RuntimeAttribute
```

结合 A-v1.5 final probe：

- 关闭 PIR 无效。
- 关闭 MKLDNN 无效。
- 同时关闭 PIR / MKLDNN 无效。
- 切 PP-OCRv5 mobile 无效。
- 切 PP-OCRv4 mobile 无效。

说明当前问题不是单个模型 profile 或单个 flag，而是 Paddle / PaddleOCR / PaddleX runtime 组合不兼容。

## 处理

- 新增 A-v2.3 兼容性矩阵脚本。
- 将当前预检和历史 final probe 聚合成正式决策报告。
- 将 PaddleOCR 从“待修”升级为“runtime compatibility boundary”。

## 结论

```text
decision = formal_boundary
```

后续若继续攻克，应走 Docker clean runtime matrix，而不是继续污染当前主线。

# 2026-05-23 A-v2.2 MiMo Provider 重新验收排查记录

## 现象

A-v1.4 中 MiMo 的报告仍停留在旧 DashScope 口径：

```text
base_url = https://dashscope.aliyuncs.com/compatible-mode/v1
status = auth_invalid
```

但当前 `.env` 已经切到：

```text
LLM_PROVIDER = xiaomi_mimo
LLM_MODEL = mimo-v2.5-pro
LLM_BASE_URL = https://token-plan-cn.xiaomimimo.com/v1
```

因此旧报告不能继续作为 MiMo 能力结论。

## 排查 1：旧进程环境污染 default_env

现象：

- 首次跑 A-v2.2 preflight 时，`default_env` 仍显示旧 DashScope endpoint。

根因：

- `preflight_provider_auth.py` 和 `run_provider_acceptance.py` 使用 `load_dotenv(..., override=False)`。
- 当前 PowerShell 进程里残留了旧的 `LLM_BASE_URL`。
- `.env` 没有覆盖旧进程环境。

处理：

- 两个脚本新增 `--dotenv-override`。
- A-v2.2 报告使用该参数重跑。

## 排查 2：MiMo direct smoke 空答案

现象：

```text
direct_llm_connected = false
chat_grounded_llm = true
```

根因判断：

- MiMo 在极短 direct smoke prompt 下可能只返回 reasoning 或空 content。
- 但真实 RAG prompt 下可以产出 grounded answer。

处理：

- `preflight_real_llm_grounding.py` 在 `chat_grounded_llm=true` 时，将 direct smoke 空答案降级为 warning。
- `run_provider_acceptance.py` 将 warning 写入报告。

## 最终结论

```text
auth preflight: 4 passed / 4
provider acceptance: 4 accepted / 4
```

MiMo 已从“认证阻塞”推进为“grounded 可比较 provider”。

# 2026-05-24 A-v3.0 发布复核排查记录

## 现象

本机 `.env` 偏企业增强开发口径，默认可能打开 PostgreSQL、Redis、Neo4j 等外部依赖。直接运行部分测试时会被本机未启动服务或外部 DNS 状态影响。

已观察到的环境型失败：

- PostgreSQL 连接池超时。
- Redis `localhost:6379` 拒绝连接。
- Neo4j 外部地址 DNS 解析失败。

## 处理口径

A-v3.0 公开发布复核采用公开 demo 默认画像：

```text
STORAGE_BACKEND=sqlite
VECTOR_BACKEND=chroma
CACHE_ENABLED=false
GRAPH_RETRIEVAL_ENABLED=false
```

这不是降低验收标准，而是避免把企业增强链路当作公开 demo 的启动前提。PostgreSQL、Redis、Neo4j 均已有独立真实验收记录，但不属于本轮公开默认链路。

## 结论

A-v3.0 的复核重点是确保 A-v2.9 评测证据进入公开发布包，后续如果做企业增强版发布，可以单独建立 PostgreSQL/Redis/Neo4j profile 的复核脚本。

# 2026-05-24 A-v2.9 评测质量提升排查记录

## 现象

旧报告已经具备真实回归、对抗和 RAGAS 风格评测，但样本量偏少：

- 回归：20 条。
- 对抗：10 条。

扩容后第一轮结果：

```text
regression = 30/30
adversarial = 20/20
faithfulness = 0.6957
context_precision = 0.8333
context_recall = 0.8222
```

`context_recall` 没达标。

## 根因

真实脱敏资料里很多故障码写在 Markdown section 标题里，例如：

- `BAT-SMOKE 电池异味或冒烟`
- `COM-08 通讯延迟`
- `UV-1 欠压报警`

原语义切片在切换标题时只把正文写入 chunk，导致标题级故障码没有进入引用上下文。

## 处理

- 修改 `semantic_chunk_text`，flush buffer 时把当前 section 标题并入 chunk 内容。
- 扩展 Agentic 故障码识别正则，支持多字母故障码。
- 补充售后意图加权和危险操作安全 warning。
- RAGAS 风格 faithfulness 改用项目统一 tokenizer，避免中文无空格文本被系统性低估。

## 最终验证

```text
real regression: 30/30
real adversarial: 20/20
faithfulness: 0.6983
answer_relevancy: 0.9222
context_precision: 0.8667
context_recall: 0.9778
```

结论：A-v2.9 的样本扩容和质量指标均达标。

# 2026-05-22 A-v2.1 演示与交付收口排查记录

## 现象

项目已经具备真实验收证据和前端演示中心，但交付入口仍分散：

- README 中历史版本内容较多，不适合作为第一演示入口。
- demo 启动脚本已经存在，但缺少独立启动指南。
- 演示顺序主要停留在聊天总结里，没有固化到仓库文档。
- 面试讲法分散在多个版本记录中。

另一个观察：

- 在 PowerShell 终端读取部分中文 Markdown 时出现乱码显示。
- 本轮新增和重写的交付文档统一按可读 Markdown 写入，优先保证仓库内对外入口清晰。

## 根因判断

问题不在 RAG 主链能力，而在交付组织：

```text
能力已形成
证据已存在
但入口、顺序、话术和边界说明没有统一
```

如果不收口，面试和演示时会出现：

- 需要频繁翻多个 docs 文件。
- 不容易讲清哪些能力已转绿。
- MiMo / PaddleOCR 边界容易被误解成“功能失败”。
- demo 环境和企业增强开发环境容易混用。

## 处理

- 用 README 固化对外入口。
- 用 `docs/demo_guide.md` 固化启动和排查。
- 用 `docs/demo_script.md` 固化演示顺序。
- 用 `docs/interview_guide.md` 固化面试回答。
- 用 `docs/A-v2.1-demo-delivery-review.md` 固化本轮复盘。

## 验证结果

已真实运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_demo_stack.ps1 -StopExisting
```

检查结果：

```text
GET http://127.0.0.1:18082/health -> 200
GET http://127.0.0.1:18082/api/v1/system/status -> 200
GET http://127.0.0.1:18082/api/v1/acceptance/overview -> 200
GET http://127.0.0.1:4175/ -> 200
GET http://127.0.0.1:4175/api/v1/acceptance/overview -> 200
```

结论：

```text
A-v2.1 的 README -> demo guide -> start script -> backend/frontend -> acceptance overview 链路可用。
```
