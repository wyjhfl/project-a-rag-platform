# A-v2.1 Demo 启动指南

## 目标

本指南用于启动公开演示画像：

```text
sqlite + chroma + deepseek-chat + FastAPI + Vue 演示中心
```

这个画像不依赖 PostgreSQL、Redis、Neo4j、Milvus 或真实 OCR runtime，适合面试和本地作品展示。

## 前置条件

- Windows PowerShell 可用。
- Python 已安装，且项目后端依赖已安装。
- `frontend/node_modules` 已存在；如果不存在，先在 `frontend/` 下执行 `npm install`。
- `.env` 中已经配置真实 `DEEPSEEK_API_KEY`。

## 配置

复制 demo 配置模板：

```powershell
copy .env.demo.example .env.demo
```

`.env.demo.example` 不包含密钥，可以提交到仓库。

真实密钥仍放在 `.env`：

```text
DEEPSEEK_API_KEY=你的真实 key
```

启动脚本会自动把 `DEEPSEEK_API_KEY` 映射为 demo 链路使用的 `LLM_API_KEY`。

## 启动

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_demo_stack.ps1 -StopExisting
```

脚本会执行：

- 读取 `.env`
- 读取 `.env.demo`，不存在时读取 `.env.demo.example`
- 固化 `sqlite + chroma + deepseek-chat`
- 关闭 Redis / Neo4j 等企业增强依赖
- 启动 FastAPI
- 启动 Vue / Vite
- 等待后端 `/health` 和前端首页 ready

默认地址：

- 后端：http://127.0.0.1:18082
- 前端：http://127.0.0.1:4175

## 验证

启动成功后依次访问：

```text
http://127.0.0.1:18082/health
http://127.0.0.1:18082/api/v1/system/status
http://127.0.0.1:18082/api/v1/acceptance/overview
http://127.0.0.1:4175/
http://127.0.0.1:4175/api/v1/acceptance/overview
```

期望结果：

- 后端健康检查返回 200。
- 系统状态返回 200。
- 验收中心接口返回 200。
- 前端首页返回 200。
- 前端代理到验收中心接口返回 200。

## 停止

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop_demo_stack.ps1
```

停止脚本会优先使用 `tmp/demo_backend.pid` 和 `tmp/demo_frontend.pid`，并清理默认端口上的残留进程。

## 常见问题

### 缺少 DEEPSEEK_API_KEY

现象：

```text
DEEPSEEK_API_KEY is missing
```

处理：

- 把真实 key 放入 `.env`。
- 不要放进 `.env.demo.example`。

### 后端启动失败

查看日志：

```text
tmp/demo_backend.out.log
tmp/demo_backend.err.log
```

重点检查：

- Python 依赖是否安装。
- 当前端口 `18082` 是否被占用。
- `.env` 中是否有错误的强制配置。

### 前端启动失败

查看日志：

```text
tmp/demo_frontend.out.log
tmp/demo_frontend.err.log
```

重点检查：

- 是否执行过 `npm install`。
- `frontend/node_modules/.bin/vite.cmd` 是否存在。
- 当前端口 `4175` 是否被占用。

### 不要直接用默认 `.env` 做公开演示

当前 `.env` 偏企业增强开发口径，可能启用：

- PostgreSQL
- Redis
- Neo4j
- 其他增强依赖

公开演示请使用 demo 脚本，它会强制切回稳定画像。
