# E2E 测试指南

> **Note**: Complete E2E tests require the demo service to be running. The `npm run e2e -- --list` command only lists tests without running them.

## 目标

通过 Playwright 对前端演示中心进行端到端冒烟测试，验证：

- 页面可正常加载，不白屏、不崩溃
- 导航切换正常
- 关键交互（API Key 配置、确认弹窗、搜索）可执行
- data-testid 定位稳定，不依赖文本或 CSS 类名

## 前置条件

- Node.js 20+
- 前端依赖已安装：`npm install`
- 前端已构建：`npm run build`
- Playwright 浏览器已安装：`npx playwright install chromium`

## Demo 启动

E2E 测试需要后端 API 和前端服务同时运行。

### 启动后端

```powershell
# 在项目根目录
python -m uvicorn app.main:app --host 0.0.0.0 --port 18082 --app-dir backend
```

### 启动前端

```powershell
Set-Location frontend
npm run build
npx vite preview --host 0.0.0.0 --port 4175
```

默认 baseURL 为 `http://127.0.0.1:4175`，与 playwright.config.ts 一致。

### 一键检查服务

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e_demo_smoke.ps1
```

此脚本检查：
- 后端 `healthz` / `readyz` 是否可访问
- 前端页面是否可访问
- 如果不可访问，给出启动命令提示

### 一键运行完整 E2E

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_full_e2e_demo.ps1
```

此脚本先检查服务，再运行 `npm run e2e`。

## Playwright 浏览器安装

首次运行前需安装 Chromium：

```powershell
npx playwright install chromium
```

如需系统依赖（Linux CI 环境）：

```bash
npx playwright install chromium --with-deps
```

## 运行命令

```powershell
# 无头模式（默认）
npm run e2e

# 有头模式（可见浏览器窗口）
npm run e2e:headed

# Playwright UI 模式
npm run e2e:ui
```

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `PLAYWRIGHT_BASE_URL` | `http://127.0.0.1:4175` | 前端服务地址 |

示例：

```powershell
$env:PLAYWRIGHT_BASE_URL = "http://localhost:5173"
npm run e2e
```

## 测试覆盖表

| Spec 文件 | 覆盖页面 | 测试用例数 | 关键验证 |
|---|---|---|---|
| acceptance.spec.ts | 验收中心 | 2 | 默认页面可见、非空白 |
| system-status.spec.ts | 系统状态 | 4 | healthz/readyz/legacy 卡片、降级不崩溃 |
| api-key.spec.ts | API Key 配置 | 3 | 弹窗打开、保存、清除 |
| documents.spec.ts | 资料管理 | 2 | 页面可见、确认弹窗可取消 |
| jobs.spec.ts | 异步任务 | 3 | 列表区域、空状态/表格、搜索 404 |
| audit.spec.ts | 审计日志 | 3 | 不崩溃、权限错误或内容、metadata 弹窗 |
| tickets.spec.ts | 工单闭环 | 2 | 启动按钮可见、确认弹窗可取消 |
| evaluations.spec.ts | 评测中心 | 2 | 页面可见、确认弹窗可取消 |

**总计：21 个测试用例**

## 常见失败原因

| 问题 | 原因 | 解决方案 |
|---|---|---|
| `page.goto: net::ERR_CONNECTION_REFUSED` | 前端服务未启动 | 先启动 `npx vite preview --port 4175` |
| `Timeout 30000ms exceeded` | 页面加载慢或后端不可达 | 确认后端运行或检查网络 |
| `locator.waitFor: waiting for selector` | data-testid 缺失或组件未渲染 | 检查对应 Vue 组件是否已添加 data-testid |
| `browserType.launch: Executable doesn't exist` | Chromium 未安装 | 运行 `npx playwright install chromium` |
| 测试通过但截图显示空白 | 后端 API 超时，前端显示加载中 | 确认后端服务可达 |

## CI 集成

CI 中通过 `workflow_dispatch` 手动触发 E2E 测试：

1. 进入 GitHub Actions 页面
2. 选择 "CI" workflow
3. 点击 "Run workflow"
4. 等待 `e2e-smoke` job 完成

`e2e-smoke` job 不会在 push/PR 时自动运行，避免阻塞主 CI 流程。

> **注意**：`e2e-smoke` 仅启动前端 preview 服务，不启动后端。因此这是 **UI 冒烟测试**，验证页面可加载、导航可切换、交互不崩溃，而非完整业务 E2E。后端 API 依赖的测试（如数据提交、真实写入）不在覆盖范围内。

## data-testid 参考表

| data-testid | 组件 | 用途 |
|---|---|---|
| `nav-acceptance` | AppShell | 验收中心导航按钮 |
| `nav-status` | AppShell | 系统状态导航按钮 |
| `nav-documents` | AppShell | 资料管理导航按钮 |
| `nav-jobs` | AppShell | 异步任务导航按钮 |
| `nav-audit` | AppShell | 审计日志导航按钮 |
| `nav-chat` | AppShell | 诊断问答导航按钮 |
| `nav-tickets` | AppShell | 工单闭环导航按钮 |
| `nav-eval` | AppShell | 评测中心导航按钮 |
| `api-key-config-button` | AppShell | API Key 配置按钮 |
| `page-acceptance` | App.vue | 验收中心页面容器 |
| `page-status` | App.vue | 系统状态页面容器 |
| `page-documents` | App.vue | 资料管理页面容器 |
| `page-jobs` | App.vue | 异步任务页面容器 |
| `page-audit` | App.vue | 审计日志页面容器 |
| `page-chat` | App.vue | 诊断问答页面容器 |
| `page-tickets` | App.vue | 工单闭环页面容器 |
| `page-eval` | App.vue | 评测中心页面容器 |
| `api-key-input` | ApiKeyConfig | API Key 输入框 |
| `api-key-role-group` | ApiKeyConfig | 角色选择单选组 |
| `api-key-clear-button` | ApiKeyConfig | 清除密钥按钮 |
| `api-key-save-button` | ApiKeyConfig | 保存按钮 |
| `job-search-input` | JobsPage | Job ID 搜索输入框 |
| `job-search-button` | JobsPage | 查询按钮 |
| `ingest-async-button` | DocumentsPage | 异步入库按钮 |
| `eval-async-button` | EvaluationsPage | 异步评测按钮 |
| `ticket-start-button` | TicketsPage | 启动工单按钮 |
