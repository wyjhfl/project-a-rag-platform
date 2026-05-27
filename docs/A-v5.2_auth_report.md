# A-v5.2 认证与最小权限边界报告

## 目标

用 FastAPI Dependency 实现 API Key + 三层角色权限，默认关闭认证，开启后保护业务接口。

## 实现方式

FastAPI `Depends(require_role("xxx"))`，不用中间件。

## 角色层级

viewer < operator < admin（高角色隐含低角色权限）

## 权限矩阵

| 接口 | 方法 | 角色 |
|------|------|------|
| /healthz | GET | 公开 |
| /readyz | GET | 公开 |
| /health | GET | 公开 |
| /api/v1/system/status | GET | viewer |
| /api/v1/acceptance/overview | GET | viewer |
| /api/v1/chat | POST | viewer |
| /api/v1/chat/session | POST | viewer |
| /api/v1/chat/stream | POST | viewer |
| /api/v1/tickets | GET | viewer |
| /api/v1/documents/ingest | POST | operator |
| /api/v1/documents/upload | POST | operator |
| /api/v1/tickets/start | POST | operator |
| /api/v1/tickets/{id}/resume | POST | operator |
| /api/v1/tickets/{id}/close | POST | operator |
| /api/v1/evaluations/run | POST | admin |

## 认证行为

| 条件 | HTTP | detail |
|------|------|--------|
| AUTH_ENABLED=false | 正常响应 | — |
| AUTH_ENABLED=true，无 key | 401 | Missing API key |
| AUTH_ENABLED=true，key 无效 | 401 | Invalid API key |
| AUTH_ENABLED=true，key 有效但角色不足 | 403 | Insufficient permissions |
| AUTH_ENABLED=true，未配置任何 key | 503 | Auth is enabled but no API keys are configured |

## 配置项

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| AUTH_ENABLED | 是否开启认证 | false |
| VIEWER_API_KEY | viewer 角色 key | 空 |
| OPERATOR_API_KEY | operator 角色 key | 空 |
| ADMIN_API_KEY | admin 角色 key | 空 |

请求头：`X-API-Key: <key>`

## 验证结果

| 检查项 | 结果 |
|--------|------|
| ruff check | All checks passed! |
| pytest test_auth.py | 9 passed |
| pytest test_health_readiness.py | 10 passed |

## 风险边界

- 日志不记录 key 值
- 健康检查端点始终公开
- 测试使用硬编码 key，不依赖真实密钥
- 未实现 JWT/OAuth、rate limiting、key 轮换、审计日志
