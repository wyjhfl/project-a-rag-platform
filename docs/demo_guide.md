# Demo Guide - Project A

## 推荐方式：一键 Full E2E Demo

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_full_e2e_demo.ps1 `
  -PythonExe "D:\path\to\Python312\python.exe" `
  -NpmCmd "D:\path\to\nodejs\npm.cmd"
```

脚本会：

1. 清理 8000 / 4173 端口上的旧进程。
2. 启动 FastAPI 后端。
3. 构建并启动 Vite preview。
4. 运行 Playwright E2E。
5. 结束后清理进程。

## 默认地址

| 服务 | 地址 |
|---|---|
| 前端控制台 | http://127.0.0.1:4173 |
| healthz | http://127.0.0.1:8000/healthz |
| readyz | http://127.0.0.1:8000/readyz |
| metrics | http://127.0.0.1:8000/metrics |
| OpenAPI | http://127.0.0.1:8000/openapi.json |

## 手动启动

### 后端

```powershell
$env:AUTH_ENABLED="false"
$env:STORAGE_BACKEND="sqlite"
$env:VECTOR_BACKEND="chroma"
$env:RATE_LIMIT_ENABLED="false"
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 前端

```powershell
cd frontend
$env:VITE_API_BASE="http://127.0.0.1:8000"
npm run build
npm run preview
```

## 面试前检查

```powershell
python -m pytest backend/tests -q
python -m ruff check backend scripts
npm --prefix frontend run build
npm --prefix frontend run e2e -- --list
```

完整生产验收：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\final_production_acceptance.ps1 `
  -PythonExe "D:\path\to\Python312\python.exe" `
  -NpmCmd "D:\path\to\nodejs\npm.cmd" `
  -RunFullE2E
```

## 讲解顺序

1. Acceptance：先讲面试展示入口。
2. Architecture：讲系统分层、RAG 数据流、Worker、可观测性和生产验收门禁。
3. Quality：讲 RAG 指标、Bad Case、Trace 和工程取舍。
4. System Status：讲健康检查、release 和 metrics。
5. Documents + Jobs：讲资料入库和异步任务。
6. Chat：讲 grounded answer 与引用证据。
7. Tickets：讲人工升级闭环。
8. Evaluations：讲评测闭环。
9. Audit：讲 Request ID 与审计追踪。
