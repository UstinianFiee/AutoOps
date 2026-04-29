<template>
  <div>
    <el-card shadow="never" style="margin-bottom: 16px">
      <el-form :model="queryForm" inline>
        <el-form-item label="LogQL 查询">
          <el-input
            v-model="queryForm.query"
            placeholder='{job="varlogs"} |= "error"'
            style="width: 400px"
          />
        </el-form-item>
        <el-form-item label="条数">
          <el-input-number v-model="queryForm.limit" :min="10" :max="1000" :step="50" />
        </el-form-item>
        <el-form-item label="方向">
          <el-select v-model="queryForm.direction" style="width: 120px">
            <el-option label="最新优先" value="backward" />
            <el-option label="最早优先" value="forward" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="search" :icon="Search">查询</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 快捷标签 -->
      <div style="margin-top: 8px">
        <span style="font-size: 12px; color: #909399; margin-right: 8px">快捷查询：</span>
        <el-tag
          v-for="q in quickQueries"
          :key="q.label"
          size="small"
          style="cursor: pointer; margin-right: 6px"
          @click="queryForm.query = q.query"
        >
          {{ q.label }}
        </el-tag>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span>查询结果 <el-tag size="small" type="info">{{ lines.length }} 条</el-tag></span>
      </template>
      <el-empty v-if="!lines.length && !loading" description="暂无日志，请执行查询" />
      <div class="log-container" v-if="lines.length">
        <div
          v-for="(line, i) in lines"
          :key="i"
          class="log-line"
          :class="logLevel(line.msg)"
        >
          <span class="log-ts">{{ formatTs(line.ts) }}</span>
          <span class="log-labels" v-if="line.labels.job">[{{ line.labels.job }}]</span>
          <span class="log-msg" v-html="highlight(line.msg)" />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { Search } from '@element-plus/icons-vue'
import api from '@/api'
import dayjs from 'dayjs'

const lines = ref([])
const loading = ref(false)

const queryForm = reactive({
  query: '{job="varlogs"}',
  limit: 100,
  direction: 'backward',
})

const quickQueries = [
  { label: '系统日志', query: '{job="varlogs"}' },
  { label: 'Docker 容器', query: '{job="docker"}' },
  { label: 'Nginx 访问', query: '{job="nginx"}' },
  { label: '错误日志', query: '{job="varlogs"} |= "error"' },
  { label: '警告日志', query: '{job="varlogs"} |= "warn"' },
  { label: 'AutoOps后端', query: '{container="autoops-backend"}' },
  { label: 'AutoOps前端', query: '{container="autoops-frontend"}' },
]

function formatTs(ts) {
  // Loki 返回纳秒时间戳
  const ms = parseInt(ts) / 1e6
  return dayjs(ms).format('YYYY-MM-DD HH:mm:ss.SSS')
}

function logLevel(msg) {
  const m = msg.toLowerCase()
  if (m.includes('error') || m.includes('fatal') || m.includes('crit')) return 'level-error'
  if (m.includes('warn')) return 'level-warn'
  if (m.includes('info')) return 'level-info'
  return ''
}

function highlight(msg) {
  return msg
    .replace(/\b(error|fatal|critical)\b/gi, '<span class="hl-error">$1</span>')
    .replace(/\b(warn|warning)\b/gi, '<span class="hl-warn">$1</span>')
    .replace(/\b(info)\b/gi, '<span class="hl-info">$1</span>')
}

async function search() {
  loading.value = true
  try {
    const res = await api.get('/logs/query', { params: queryForm })
    lines.value = res.data.lines
  } finally {
    loading.value = false
  }
}

function reset() {
  queryForm.query = '{job="varlogs"}'
  queryForm.limit = 100
  queryForm.direction = 'backward'
  lines.value = []
}
</script>

<style scoped>
.log-container {
  background: #1e1e1e;
  border-radius: 4px;
  padding: 8px;
  max-height: 600px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
}

.log-line {
  padding: 2px 4px;
  border-radius: 2px;
  line-height: 1.6;
  display: flex;
  gap: 8px;
  align-items: baseline;
}

.log-line:hover { background: rgba(255,255,255,0.05); }

.log-ts { color: #6a9955; white-space: nowrap; flex-shrink: 0; }
.log-labels { color: #569cd6; white-space: nowrap; flex-shrink: 0; }
.log-msg { color: #d4d4d4; word-break: break-all; }

.level-error { background: rgba(245, 108, 108, 0.1); }
.level-warn { background: rgba(230, 162, 60, 0.1); }
.level-info { background: rgba(64, 158, 255, 0.05); }
</style>

<style>
.hl-error { color: #f56c6c; font-weight: bold; }
.hl-warn { color: #e6a23c; font-weight: bold; }
.hl-info { color: #409eff; }
</style>
