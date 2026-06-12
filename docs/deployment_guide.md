# 部署指南

## 概述

Project A RAG 平台支持两种部署模式：

| 模式 | 适用场景 | 存储 | 向量库 | 认证 |
|---|---|---|---|---|
| Demo | 本地演示、开发调试 | SQLite | Chroma | 默认关闭 |
| Production | 生产环境 | PostgreSQL | Chroma / Milvus | 建议开启 |

---

## Demo 模式部署

### 前置条件

- Python 3.11+
- Node.js 20+
- npm

### 快速启动

使用项目提供的 PowerShell 脚本一键启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_full_e2e_demo.ps1
```

脚本会自动：
1. 启动后端（FastAPI，默认端口 8000）
2. 安装前端依赖并构建
3. 启动前端预览服务（默认端口 4175）

### 手动启动

**后端：**

```powershell
pip install -e .
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**前端：**

```powershell
cd frontend
npm install
npm run build
npx vite preview --host 0.0.0.0 --port 4175
```

### 停止服务

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e_demo_smoke.ps1
```

---

## Production 模式部署

### 前置条件

- Docker & Docker Compose
- PostgreSQL 实例（或使用 Docker Compose 内置）
- Redis 实例（可选，用于缓存）
- Milvus 实例（可选，用于大规模向量检索）

### 环境配置

1. 复制生产环境配置模板：

```powershell
copy .env.production.example .env
```

2. 编辑 `.env` 文件，填写真实配置：

```ini
# WARNING: 不要将真实密钥提交到版本控制

# 存储配置
STORAGE_BACKEND=postgres
DATABASE_URL=postgresql://user:password@postgres:5432/project_a

# 向量库配置
VECTOR_BACKEND=chroma
# 或使用 Milvus:
# VECTOR_BACKEND=milvus
# MILVUS_URI=http://milvus:19530

# LLM 配置
LLM_PROVIDER=deepseek_chat
LLM_MODEL=deepseek-chat
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.deepseek.com

# 认证配置（生产环境建议开启）
AUTH_ENABLED=true
VIEWER_API_KEY=your-viewer-key
OPERATOR_API_KEY=your-operator-key
ADMIN_API_KEY=your-admin-key

# CORS 配置
CORS_ALLOW_ORIGINS=https://your-domain.com

# 缓存配置（可选）
CACHE_ENABLED=true
REDIS_URL=redis://redis:6379/0
```

### Docker Compose 启动

```powershell
docker compose up -d
```

生产栈包含以下服务：
- `backend`：FastAPI 应用（非 root 用户运行）
- `frontend`：Nginx 托管的前端静态文件
- `postgres`：PostgreSQL 数据库
- `redis`：Redis 缓存（可选）
- `milvus`：Milvus 向量数据库（可选）

### Demo Docker Compose

项目也提供了 `docker-compose.demo.yml` 用于快速演示：

```powershell
docker compose -f docker-compose.demo.yml up -d
```

### Bind Mount 权限

生产环境中，bind mount 的数据目录需要确保容器进程有读写权限：

```bash
sudo chown -R 1000:1000 ./data
```

### 密码一致性

确保 `.env` 中的 `POSTGRES_PASSWORD` 与 PostgreSQL 容器环境变量一致：

```ini
POSTGRES_PASSWORD=your-secure-password
```

> **注意**：`POSTGRES_PASSWORD` 必须在 `.env` 和 `docker-compose.yml` 的 postgres 服务中保持一致，否则后端无法连接数据库。

### 健康检查

| 端点 | 用途 | 说明 |
|---|---|---|
| `GET /healthz` | Liveness | 存活检查，始终返回 200 |
| `GET /readyz` | Readiness | 就绪检查，检查配置/存储/向量库状态，不可用时返回 503 |
| `GET /health` | Legacy | 兼容旧接口 |

---

## 数据持久化

### Demo 模式

数据存储在项目目录下：
- `data/app.db`：SQLite 数据库
- `data/chroma/`：Chroma 向量库
- `data/uploaded_docs/`：上传文档

### Production 模式

Docker Compose 使用命名卷持久化数据：
- `pgdata`：PostgreSQL 数据
- `chroma-data`：Chroma 向量库
- `uploaded-docs`：上传文档

---

## Schema 版本管理

系统使用 `schema_migrations` 表管理数据库版本：
- `CURRENT_SCHEMA_VERSION`：当前 schema 版本号
- 启动时自动执行迁移，重复初始化安全

---

## 升级与回滚

### 升级步骤

1. 拉取新版本代码
2. 检查 `.env.production.example` 是否有新增配置项
3. 更新 `.env` 文件
4. 重启服务：

```powershell
docker compose down
docker compose up -d
```

5. 验证健康检查：

```powershell
curl http://localhost:8000/readyz
```

### 回滚步骤

1. 切换到旧版本代码
2. 恢复 `.env` 文件
3. 重启服务
4. 如需回滚数据库，从备份恢复

---

## 常见问题

### Q: 前端构建失败

确保 Node.js 版本 ≥ 20，并先执行 `npm install`：

```powershell
cd frontend
npm install
npm run build
```

### Q: 后端启动报配置错误

检查 `.env` 文件中必填项是否完整，特别是 `LLM_PROVIDER` 和 `LLM_API_KEY`。

### Q: Docker Compose 启动失败

检查端口是否被占用，以及 `.env` 文件中数据库连接配置是否正确。

### Q: 认证相关 401/403

确认 `AUTH_ENABLED` 设置正确，API Key 已配置。前端可通过「配置密钥」按钮设置 API Key。

## Worker Service

Production deployments should run the job worker as a separate service:

```bash
# Standalone
python -m app.job_worker

# Docker
docker compose up -d worker
```

Configure via environment variables:
- `JOB_EXECUTION_MODE=worker` — Enable external worker mode
- `WORKER_ID` — Unique worker identifier (default: auto-generated)
- `JOB_POLL_INTERVAL_SECONDS` — Poll interval (default: 5)
- `JOB_DEFAULT_TIMEOUT_SECONDS` — Job timeout (default: 300)

Demo mode uses `JOB_EXECUTION_MODE=inprocess` and does not require a worker.

> **Note**: The worker now supports both `document.ingest` and `evaluation.run` job types. Unknown job types will fail.

## Database Migrations

Check migration status:

```bash
python -m app.migrations status
```

Apply pending migrations:

```bash
python -m app.migrations upgrade
```

### Backup Before Upgrade

SQLite:
```bash
cp data/app.db data/app.db.backup.$(date +%Y%m%d)
```

PostgreSQL:
```bash
pg_dump -h localhost -U project_a project_a > backup_$(date +%Y%m%d).sql
```

### Rollback

If a migration fails:
1. Stop the application.
2. Restore from backup.
3. Investigate the failure before retrying.

### Atomic Job Claim

Job claim is now an atomic store-level operation:
- **SQLite**: Conditional UPDATE with `WHERE locked_by IS NULL`
- **PostgreSQL**: `FOR UPDATE SKIP LOCKED`

This ensures safe concurrent claiming in multi-worker deployments.

## Rate Limiting

Enable in production via:
```
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST=30
```

The rate limiter enforces both:
- **RPM (Requests Per Minute)**: Total requests in a 60-second sliding window
- **Burst**: Maximum requests in a 1-second window

Both limits must be satisfied for a request to be allowed.

Health check endpoints are exempt by default.

## Metrics

Enable Prometheus-format metrics:
```
METRICS_ENABLED=true
```

Access at `GET /metrics`. Configure network-level access control for production scraping.

Metrics are now automatically recorded by the `_MetricsMiddleware` for all HTTP requests and by `JobService` for all job state transitions. No manual instrumentation needed.

## Secret Scanning

Run before commits:
```bash
python scripts/secret_scan.py --dir .
```

Integrated in CI pipeline.
