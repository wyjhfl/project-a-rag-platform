# A-v4 工程基线收口报告

## 1. 本轮目标

将项目从研发态收口为可重复运行、可交付、可维护的工程项目。不新增业务功能，只提升工程可维护性和 CI 保护。

## 2. 修改内容

### 2.1 拆出验收中心 Service

**问题**：`backend/app/main.py` 承担了约 490 行验收聚合业务逻辑（`_build_acceptance_overview` 及其 16 个辅助函数），违反单一职责。

**方案**：将验收聚合逻辑迁移到独立模块 `backend/app/acceptance/service.py`。

**修改文件**：

| 文件 | 操作 | 行数变化 |
|------|------|----------|
| `backend/app/acceptance/__init__.py` | 新建 | +3 |
| `backend/app/acceptance/service.py` | 新建 | +350 |
| `backend/app/main.py` | 修改 | 752→251 |

**关键设计决策**：
- `build_acceptance_overview()` 接受 `docs_dir` 和 `version` 参数，默认值与原行为一致
- `_latest_doc` 签名从 `(pattern)` 变为 `(docs_dir, pattern)`，因为 DOCS_DIR 不再是模块级常量
- API 返回 schema 不变，`/api/v1/acceptance/overview` 行为不变
- main.py 中路由处理器简化为 `return build_acceptance_overview(version=APP_VERSION)`

### 2.2 CI 最小补强

**问题**：CI 只跑 6 个测试文件，验收中心接口、RAG 主链、查询增强、多轮对话、切片逻辑没有 CI 保护。

**方案**：在 CI 的 Core pytest 步骤中增加 5 个测试文件。

**修改文件**：`.github/workflows/ci.yml`

**新增测试覆盖**：

| 测试文件 | 覆盖模块 |
|----------|----------|
| `test_acceptance_overview_api.py` | 验收中心接口 |
| `test_rag_pipeline.py` | RAG 主链 |
| `test_query_enhancement.py` | 查询增强 |
| `test_conversation.py` | 多轮对话 |
| `test_chunker.py` | 切片逻辑 |

CI 测试文件从 6 个增加到 11 个。

### 2.3 .gitignore 最小修正

**问题**：`.codex/` 目录没有忽略规则，IDE 缓存可能被误提交。但 `.codex/skills/project-a-rag-mentor/SKILL.md` 是项目级规则文件，不应被忽略。

**方案**：添加精确的 `.codex/` 忽略规则，逐层排除项目级 SKILL.md。

**修改文件**：`.gitignore`

**新增规则**：
```
.codex/*
!.codex/skills/
.codex/skills/*
!.codex/skills/project-a-rag-mentor/
```

## 3. 为什么只拆 acceptance service

- main.py 中约 65% 的代码是验收聚合逻辑，是最大的单一职责违反
- 验收聚合逻辑与 HTTP 路由层无关，是"读取报告→构建响应"的展示层服务
- 拆分后 main.py 只剩路由定义和基础设施初始化，职责清晰
- 其他模块（rag/、ticketing/、storage/）已经是独立包，无需调整

## 4. CI 覆盖变化

| 指标 | 修改前 | 修改后 |
|------|--------|--------|
| CI 测试文件数 | 6 | 11 |
| 验收中心覆盖 | 无 | test_acceptance_overview_api.py |
| RAG 主链覆盖 | 无 | test_rag_pipeline.py |
| 查询增强覆盖 | 无 | test_query_enhancement.py |
| 多轮对话覆盖 | 无 | test_conversation.py |
| 切片逻辑覆盖 | 无 | test_chunker.py |

## 5. 未做事项

- 未拆分 `frontend/src/App.vue`（590 行单文件组件，功能稳定，优先级低于后端收口）
- 未合并/删除 `docs/` 下旧版本文档（保留迭代历史，归档即可）
- 未重写 `docs/dev_log.md` 或 `docs/debug_log.md`（超长日志是历史记录）
- 未修改 `docker-compose.yml`（企业增强模式配置当前稳定）
- 未从 Git 跟踪中移除 `.codex/` 文件（需技术总监确认）
- 未扩展 CI 到全量 `backend/tests/`（部分测试依赖外部服务）

## 6. 验证命令和结果

### 6.1 AST 语法验证

```bash
python -c "import ast; ast.parse(open('backend/app/acceptance/service.py').read()); print('service.py: AST OK'); ast.parse(open('backend/app/main.py').read()); print('main.py: AST OK')"
```

结果：`service.py: AST OK` / `main.py: AST OK` ✓

### 6.2 验收中心 Service 独立运行验证

```python
from app.acceptance.service import build_acceptance_overview
result = build_acceptance_overview(version='v2.0')
print('status:', result.status, 'panels:', len(result.panels))
```

结果：`status: ok` / `panels: 4` / `provider: passed` / `multimodal: passed` / `evaluation: passed` / `badcases: passed` ✓

### 6.3 验收中心接口测试

```bash
python -m pytest backend/tests/test_acceptance_overview_api.py -q
```

结果：`1 passed` ✓

### 6.4 核心接口测试

```bash
python -m pytest backend/tests/test_api.py backend/tests/test_ticket_workflow.py backend/tests/test_release_scenarios.py -q
```

结果：`14 passed` ✓

### 6.5 前端构建

```bash
cd frontend && npm run build
```

结果：`✓ built in 30.02s` ✓

### 6.6 未运行的验证

- **全量后端测试** (`python -m pytest backend/tests -q`)：部分测试依赖外部服务（Redis、Neo4j、Milvus），在当前环境无法运行。CI 环境会通过 mock 覆盖。
- **新增 CI 测试文件单独验证**（test_rag_pipeline.py、test_query_enhancement.py、test_conversation.py、test_chunker.py）：这些测试在 CI 环境中运行，本地环境缺少部分依赖。

## 7. A-v4.4 提交前安全修正

### 7.1 仓库边界修复

- 仓库根目录实际是 `天空没有极限`，不是 `project-a-rag-platform/`。
- `七月v0.3/` 已从 Git 索引移除（37 个文件），磁盘文件未删除。
- 根目录 `.gitignore` 需追加 `七月v0.3/`（需手动完成，工具路径限制无法自动修改）。

### 7.2 本地路径替换

- `preflight_multimodal_linux_runtime.py`：`WSL_REPO_PATH` 和 `WSL_USER_LIBGOMP_PATH` 改为环境变量读取，默认值不含真实用户名。
- `preflight_mineru_linux_runtime.py`：`WSL_PATH` 改为环境变量 `MINERU_WSL_PATH` 读取，默认值使用 `$HOME`。

### 7.3 公开导出路径脱敏

- `create_public_release_repo.py` 新增 `sanitize_text()` 函数，复制文本文件时自动替换本地路径占位符。
- 替换模式：Windows 路径 → `<LOCAL_REPO_ROOT>`，WSL 路径 → `<WSL_HOME>`，下载目录 → `<LOCAL_DOWNLOAD_DIR>`。
- 新增 `test_public_release_sanitization.py` 覆盖 7 个测试用例。

### 7.4 敏感 Key 提醒

- `.env` 中真实 DeepSeek Key 已泄露，虽未被 Git 跟踪，但用户必须自行轮换。
