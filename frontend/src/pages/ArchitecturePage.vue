<template>
  <section class="stack">
    <el-card class="architecture-hero" data-testid="architecture-overview-card">
      <template #header>
        <div class="card-header-row">
          <span>架构总览</span>
          <el-tag type="success" size="small">interview-ready</el-tag>
        </div>
      </template>
      <p class="muted">
        这页用于面试时从 UI 直接讲清楚 Project A 的系统分层、RAG 数据流、异步任务流、可观测性和生产验收门禁。
      </p>
      <div class="architecture-actions section">
        <el-button data-testid="architecture-copy-mermaid" type="primary" @click="copyArchitectureMermaid">
          复制 Mermaid 架构图
        </el-button>
        <span class="muted">复制后可粘贴到 README、PPT 或面试笔记中。</span>
      </div>
    </el-card>

    <el-card data-testid="architecture-layer-map">
      <template #header>系统分层</template>
      <div class="layer-grid">
        <div v-for="layer in layers" :key="layer.title" class="layer-card">
          <span class="layer-kicker">{{ layer.kicker }}</span>
          <strong>{{ layer.title }}</strong>
          <p class="muted">{{ layer.summary }}</p>
          <div class="tag-row">
            <el-tag v-for="tag in layer.tags" :key="tag" size="small" type="info">{{ tag }}</el-tag>
          </div>
        </div>
      </div>
    </el-card>

    <div class="flow-grid">
      <el-card data-testid="architecture-rag-flow">
        <template #header>RAG 数据流</template>
        <ol class="flow-list">
          <li v-for="step in ragFlow" :key="step">{{ step }}</li>
        </ol>
      </el-card>

      <el-card data-testid="architecture-job-flow">
        <template #header>Job / Worker 流</template>
        <ol class="flow-list">
          <li v-for="step in jobFlow" :key="step">{{ step }}</li>
        </ol>
      </el-card>
    </div>

    <div class="flow-grid">
      <el-card data-testid="architecture-observability-flow">
        <template #header>可观测性链路</template>
        <ol class="flow-list">
          <li v-for="step in observabilityFlow" :key="step">{{ step }}</li>
        </ol>
      </el-card>

      <el-card data-testid="architecture-acceptance-gate">
        <template #header>生产验收门禁</template>
        <p class="muted">最终交付使用一个脚本做总门禁：</p>
        <pre class="command">powershell -ExecutionPolicy Bypass -File .\scripts\final_production_acceptance.ps1 -RunFullE2E</pre>
        <ul class="flow-list">
          <li v-for="item in acceptanceGate" :key="item">{{ item }}</li>
        </ul>
      </el-card>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from '../plugins/element-plus'

const architectureMermaid = `flowchart LR
  User[User / Interviewer] --> Web[Vue 3 Operations Console]
  Web --> API[FastAPI API]
  API --> RAG[RAG Pipeline]
  API --> Jobs[JobService / Worker]
  API --> Audit[Audit Events]
  API --> Metrics[Prometheus /metrics]
  RAG --> Vector[Chroma / Hybrid Retrieval]
  RAG --> LLM[LLM Provider]
  Jobs --> Store[(SQLite / PostgreSQL)]
  API --> Redis[(Redis Rate Limit)]
  Web --> OpenAPI[OpenAPI-generated Types]`

const layers = [
  {
    kicker: 'UI',
    title: 'Vue 3 运维控制台',
    summary: 'Acceptance、Quality、Architecture、System Status、Jobs、Audit 等页面把工程能力变成可演示产品。',
    tags: ['Vue 3', 'Vite', 'Element Plus', 'Playwright'],
  },
  {
    kicker: 'API',
    title: 'FastAPI 服务层',
    summary: '统一 REST API、X-API-Key 角色、统一错误体、Request ID、OpenAPI schema。',
    tags: ['FastAPI', 'Pydantic', 'OpenAPI', 'Auth'],
  },
  {
    kicker: 'AI',
    title: 'RAG Pipeline',
    summary: '围绕 grounded answer、引用证据、Prompt 注入防护和资料不足拒答设计。',
    tags: ['RAG', 'grounded', 'citations', 'guardrails'],
  },
  {
    kicker: 'Async',
    title: 'JobService / Worker',
    summary: 'claim_next_job、heartbeat、cancel、retry、timeout 支撑异步入库和评测。',
    tags: ['Worker', 'PostgreSQL', 'Redis', 'stress'],
  },
  {
    kicker: 'Ops',
    title: 'Observability',
    summary: 'healthz、readyz、Prometheus metrics、audit events 和 Request ID 形成排障链路。',
    tags: ['Prometheus', 'Audit', 'Request ID', 'readyz'],
  },
  {
    kicker: 'Gate',
    title: 'Production Acceptance',
    summary: 'final_production_acceptance.ps1 串起测试、构建、OpenAPI、secret scan、Docker、smoke、Full E2E。',
    tags: ['pytest', 'ruff', 'Docker', 'E2E'],
  },
]

const ragFlow = [
  '用户输入设备型号、故障码或现场现象。',
  'PromptInjectionGuard 检查对抗输入。',
  'Retriever 从 Chroma / hybrid retrieval 中召回资料。',
  'LLM 基于上下文生成 grounded answer 和 citations。',
  '资料不足或高风险时拒答或升级人工工单。',
]

const jobFlow = [
  '前端创建 document.ingest 或 evaluation.run job。',
  'JobService 写入 PENDING 状态。',
  'Worker 通过 claim_next_job 抢占任务并进入 RUNNING。',
  '长任务持续 heartbeat，避免被误判 timeout。',
  '任务完成后写入 SUCCEEDED / FAILED / CANCELLED、audit 和 metrics。',
]

const observabilityFlow = [
  'ApiErrorAlert 展示统一错误和 request_id。',
  'Audit events 记录 job、评测、工单等关键事件。',
  'Prometheus /metrics 暴露 request/error/job/uptime 指标。',
  'System Status 聚合 healthz、readyz、release 和 metrics summary。',
]

const acceptanceGate = [
  'Full backend tests + ruff。',
  'Frontend build + Playwright E2E list/full run。',
  'OpenAPI drift check + generated frontend types。',
  'Secret scan + Docker Compose config。',
  'PostgreSQL smoke + Redis rate limit smoke + worker stress。',
]

async function copyArchitectureMermaid() {
  try {
    await navigator.clipboard.writeText(architectureMermaid)
    ElMessage.success('已复制 Mermaid 架构图')
  } catch {
    ElMessage.warning('当前浏览器不支持自动复制，请手动选择架构图文本')
  }
}
</script>

<style scoped>
.architecture-hero {
  border: 1px solid #d9ecff;
  background: linear-gradient(135deg, #f8fbff 0%, #ffffff 50%, #f8fff5 100%);
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.architecture-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.layer-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.layer-card {
  padding: 14px;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  background: #fff;
}

.layer-kicker {
  display: block;
  margin-bottom: 6px;
  color: #909399;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.layer-card strong {
  color: #303133;
}

.layer-card p {
  margin: 6px 0 10px;
  line-height: 1.55;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.flow-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.flow-list {
  margin: 0;
  padding-left: 20px;
  color: var(--el-text-color-regular);
  line-height: 1.8;
}

.command {
  margin: 10px 0;
  padding: 10px 12px;
  overflow-x: auto;
  border-radius: 10px;
  background: #1f2937;
  color: #e5e7eb;
  white-space: pre-wrap;
}

@media (max-width: 980px) {
  .layer-grid,
  .flow-grid {
    grid-template-columns: 1fr;
  }
}
</style>
