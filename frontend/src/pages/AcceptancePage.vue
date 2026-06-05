<template>
  <section class="stack">
    <el-alert v-if="!overview" type="info" :closable="false" show-icon class="section">
      <template #title>正在加载验收概览数据…</template>
    </el-alert>

    <template v-if="overview">
      <div class="overview-header">
        <el-tag :type="overview.status === 'ok' ? 'success' : 'warning'" size="large">
          {{ overview.status === 'ok' ? '验收通过' : '部分待改进' }}
        </el-tag>
        <span class="muted">版本: {{ overview.version }}</span>
      </div>

      <div v-for="panel in overview.panels" :key="panel.key" class="panel-section">
        <el-card>
          <template #header>
            <div class="card-header-row">
              <span>{{ panel.title }}</span>
              <el-tag :type="panelStatusType(panel.status)" size="small">{{ panel.status }}</el-tag>
            </div>
          </template>

          <p>{{ panel.summary }}</p>

          <el-descriptions v-if="Object.keys(panel.metrics).length > 0" :column="2" border size="small" class="section">
            <el-descriptions-item v-for="(value, key) in panel.metrics" :key="String(key)" :label="String(key)">
              {{ value }}
            </el-descriptions-item>
          </el-descriptions>

          <div v-if="panel.breakdown.length > 0" class="section">
            <h4>分项明细</h4>
            <el-table :data="panel.breakdown" size="small" stripe>
              <el-table-column prop="label" label="项目" width="200" />
              <el-table-column prop="status" label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="panelStatusType(row.status)" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="summary" label="说明" min-width="200" />
            </el-table>
          </div>

          <div v-if="panel.chart.length > 0" class="section">
            <h4>指标图表</h4>
            <div class="chart-bars">
              <div v-for="bar in panel.chart" :key="bar.label" class="chart-bar-row">
                <span class="chart-label">{{ bar.label }}</span>
                <div class="chart-bar-track">
                  <div
                    class="chart-bar-fill"
                    :class="`tone-${bar.tone}`"
                    :style="{ width: `${(bar.value / bar.total) * 100}%` }"
                  />
                </div>
                <span class="chart-value">{{ bar.value }} / {{ bar.total }}</span>
              </div>
            </div>
          </div>

          <div v-if="panel.highlights.length > 0" class="section">
            <h4>关键发现</h4>
            <div v-for="hl in panel.highlights" :key="hl.title" class="highlight-item">
              <el-tag :type="panelStatusType(hl.status)" size="small">{{ hl.status }}</el-tag>
              <strong>{{ hl.title }}</strong>
              <p class="muted">{{ hl.summary }}</p>
              <div v-if="hl.tags.length > 0" class="tag-row">
                <el-tag v-for="tag in hl.tags" :key="tag" size="small" type="info">{{ tag }}</el-tag>
              </div>
            </div>
          </div>

          <div v-if="panel.trace_cases.length > 0" class="section">
            <h4>Trace 时间线</h4>
            <el-collapse>
              <el-collapse-item v-for="tc in panel.trace_cases" :key="tc.case_id" :title="`${tc.title} — ${tc.issue}`">
                <el-timeline>
                  <el-timeline-item v-for="(evt, idx) in tc.events" :key="idx" :timestamp="evt.name" placement="top">
                    <p>{{ evt.summary }}</p>
                    <el-descriptions v-if="Object.keys(evt.inputs).length > 0" :column="1" size="small" border>
                      <el-descriptions-item v-for="(v, k) in evt.inputs" :key="String(k)" :label="String(k)">{{ v }}</el-descriptions-item>
                    </el-descriptions>
                  </el-timeline-item>
                </el-timeline>
              </el-collapse-item>
            </el-collapse>
          </div>

          <div v-if="panel.evidence.length > 0" class="section">
            <h4>证据文件</h4>
            <ul class="evidence-list">
              <li v-for="ev in panel.evidence" :key="ev.path">
                <span class="muted">{{ ev.label }}: {{ ev.path }}</span>
              </li>
            </ul>
          </div>
        </el-card>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import type { AcceptanceOverviewResponse } from '../api/types'

defineProps<{ overview: AcceptanceOverviewResponse | null }>()

function panelStatusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'passed' || status === 'ok') return 'success'
  if (status === 'warning' || status === 'degraded') return 'warning'
  if (status === 'error' || status === 'danger') return 'danger'
  return 'info'
}
</script>

<style scoped>
.overview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.panel-section {
  margin-bottom: 16px;
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.chart-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chart-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-label {
  width: 160px;
  font-size: 13px;
  text-align: right;
}

.chart-bar-track {
  flex: 1;
  height: 16px;
  border-radius: 4px;
  background: #f0f0f0;
  overflow: hidden;
}

.chart-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.tone-success { background: #67c23a; }
.tone-warning { background: #e6a23c; }
.tone-danger { background: #f56c6c; }
.tone-info { background: #909399; }

.chart-value {
  width: 80px;
  font-size: 13px;
  color: #909399;
}

.highlight-item {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.tag-row {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}

.evidence-list {
  padding-left: 20px;
  margin: 0;
}
</style>
