# Operation Runbook

> 目标：让 Project A 不只是能演示，还能说明“出问题时怎么查”。

## 快速判断流程

当系统异常时，先按这个顺序排查：

1. 看服务是否存活：`GET /healthz`。
2. 看依赖是否就绪：`GET /readyz`。
3. 看请求错误和任务指标：`GET /metrics`。
4. 看前端错误中的 request_id。
5. 看 Audit 事件。
6. 看 RAG Trace。
7. 看 Jobs 状态。
8. 看 Tickets 状态。

## 常见故障处理

### API 返回 500

判断步骤：

- 记录前端错误里的 request_id。
- 检查 `/healthz` 是否正常。
- 检查 `/readyz` 是否 degraded。
- 检查 `/metrics` 中 error total 是否增长。
- 查看后端日志中同 request_id 的错误。

可能原因：

- 存储连接失败。
- 向量库不可用。
- LLM provider 超时或返回异常。
- 请求字段和 Pydantic 模型不匹配。

处理建议：

- 如果 readyz degraded，先修依赖。
- 如果只有某个接口失败，优先看对应服务模块。
- 如果 LLM 外部服务失败，考虑降级或拒答。

### RAG 回答质量下降

判断步骤：

- 查询对应 trace_id。
- 查看 retrieved_chunks 是否相关。
- 查看 selected_chunks 是否足够支撑答案。
- 查看 citations 是否为空或不相关。
- 查看 AgenticRetriever 是否触发 retry。
- 对照 Evaluation 结果和 bad case。

可能原因：

- 文档样本不足。
- chunk 切分不合适。
- query rewrite 不准确。
- embedding 或关键词检索召回不足。
- 生成阶段没有忠实使用上下文。

处理建议：

- 补文档或修正文档结构。
- 增加 production-like eval case。
- 调整 chunk 策略和查询增强。
- 对低分 Trace 做回归测试。

### Agentic RAG 误拒答

判断步骤：

- 查看 tool_calls 中 security_check 是否误命中。
- 查看 knowledge_search 的 retrieval_score 和 context_sufficient。
- 查看 citations 是否为空。
- 查看 insufficient 字段。

可能原因：

- PromptInjectionGuard 规则过严。
- 检索质量低。
- query rewrite 不合适。
- 文档没有覆盖该问题。

处理建议：

- 将误拒答案例加入评测集。
- 调整检索增强策略。
- 扩充文档和 citations 评测。

### 高风险问题没有升级

判断步骤：

- 查看 risk_check tool call 输出。
- 检查问题是否包含风险词。
- 检查 create_ticket_on_escalation 配置。
- 查看 Tickets 页面是否生成 ticket。
- 查看 Audit 是否记录工单事件。

可能原因：

- 风险词未覆盖。
- 用户表达和规则不匹配。
- 工单服务写入失败。
- 前端关闭了自动建工单开关。

处理建议：

- 扩充 high risk cases。
- 引入更细风险分类规则。
- 对 ticket escalation 增加回归测试。

### Jobs 卡住或失败

判断步骤：

- 打开 Jobs 页面查看状态。
- 检查 heartbeat 是否更新。
- 查看错误摘要。
- 检查 worker 是否运行。
- 检查 PostgreSQL 或 SQLite 状态。

可能原因：

- worker 未启动。
- 文档入库异常。
- 评测任务异常。
- 数据库锁竞争或连接失败。

处理建议：

- 重启 worker。
- 对失败任务查看 payload 和 error。
- 使用 PostgreSQL worker stress 验证并发 claim。
- 生产环境优先外部队列。

### Redis 限流异常

判断步骤：

- 检查 `RATE_LIMIT_ENABLED`。
- 检查 Redis URL。
- 查看 readyz 是否 degraded。
- 查看 429 错误是否异常增多。

可能原因：

- Redis 不可用。
- 限流参数过低。
- 某个客户端突增请求。

处理建议：

- 恢复 Redis。
- 调整 RPM 和 burst。
- 对高频接口增加缓存或降级。

## 面试表达

推荐说法：

> 我为项目补了运维 Runbook，不只是展示页面。API 错误先看 healthz/readyz/request_id/metrics，RAG 质量问题看 Trace、citations 和 Evaluation，高风险升级问题看 risk_check 和 Tickets，Jobs 问题看 heartbeat 和 worker 状态。这样项目从 demo 更接近真实可维护系统。
