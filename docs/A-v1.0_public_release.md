# A-v1.0 公开版发布说明

## 发布目标

本次公开版只保留项目最终实现、最小演示数据、核心测试和部署入口，目标是让仓库对外可读、可跑、可验证。

## 保留内容

- FastAPI + Vue3 的主应用代码
- 核心 RAG、工单、安全、评测入口实现
- 最小演示数据与脱敏真实资料样例
- 核心回归测试
- Docker Compose 与 GitHub Actions
- 公开版说明文档、测试结果、bad cases 摘要

## 移除内容

- `frontend/node_modules`、`frontend/dist`
- `data/chroma`、`data/v05_eval`、`data/neo4j_real_probe_chroma`
- 本地数据库、日志、PID、临时上传文件
- 下载来的原始 PDF / 大文件资料
- 大量研发过程型文档、调试记录、联调过程文件

## 默认运行原则

- 默认本地运行只依赖 SQLite + Chroma + 脱敏数据
- Redis、PostgreSQL、Milvus、Neo4j、真实多模态能力作为可选增强
- CI 不要求外部服务在线

## 推荐发布前检查

```powershell
pytest backend/tests/test_api.py `
  backend/tests/test_enterprise_api.py `
  backend/tests/test_hybrid_retrieval.py `
  backend/tests/test_rag_security.py `
  backend/tests/test_release_scenarios.py `
  backend/tests/test_ticket_workflow.py -q

python -m ruff check backend
python -m compileall backend\app backend\scripts

cd frontend
npm ci
npm run build

cd ..
docker compose config
```

## 公开仓库生成方式

```powershell
python backend/scripts/create_public_release_repo.py --target ..\project-a-rag-platform-public --force
```

生成后在新目录中：

```powershell
git init -b main
git add .
git status
```

如果你后面提供 GitHub 远端仓库地址，再执行 `git remote add origin ...` 和 `git push` 即可。
