<template>
  <div>
    <!-- 服务器选择 + 概览卡片 -->
    <div class="server-bar" style="margin-bottom:16px">
      <span style="font-size:13px;color:#64748b;margin-right:8px;white-space:nowrap">监控目标：</span>
      <el-radio-group v-model="selectedInstance" @change="loadOverview" size="small">
        <el-radio-button value="">AutoOps 本机</el-radio-button>
        <el-radio-button v-for="s in servers" :key="s.ip" :value="s.ip">
          <span :style="{ color: s.status === 'online' ? '#16a34a' : '#94a3b8' }">●</span>
          {{ s.name }}
        </el-radio-button>
      </el-radio-group>
      <el-tag
        v-if="selectedInstance && !instanceOnline"
        type="warning" size="small" style="margin-left:8px"
      >未安装监控，请在服务器管理页点击"安装监控"</el-tag>
    </div>

    <!-- 概览卡片 -->
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6" v-for="m in metricCards" :key="m.label">
        <el-card shadow="never" class="metric-card">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value" :style="{ color: m.color }">
            {{ m.value !== null ? m.value.toFixed(1) + m.unit : '-' }}
          </div>
          <el-progress
            :percentage="m.value !== null ? Math.min(m.value, 100) : 0"
            :color="m.color"
            :show-text="false"
            style="margin-top: 8px"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- Grafana 嵌入 -->
    <el-card shadow="never" style="margin-bottom: 16px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>Grafana 监控面板</span>
          <div style="display:flex;gap:8px;align-items:center">
            <el-tag v-if="grafanaOk" type="success" size="small">已连接</el-tag>
            <el-tag v-else type="warning" size="small">连接中...</el-tag>
            <el-button size="small" type="primary" @click="openGrafana">新窗口打开</el-button>
          </div>
        </div>
      </template>
      <div v-if="!grafanaOk" class="grafana-placeholder">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" style="opacity:0.3">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" stroke="#374151" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <p>Grafana 加载中，请稍候...</p>
        <p style="font-size:12px;color:#94a3b8">如长时间无法加载，请确认 Grafana 容器已启动</p>
        <el-button size="small" @click="openGrafana" style="margin-top:8px">直接访问 Grafana</el-button>
      </div>
      <iframe
        v-show="grafanaOk"
        :src="grafanaUrl"
        width="100%"
        height="500px"
        frameborder="0"
        style="border-radius: 4px; display:block"
        @load="grafanaOk = true"
        @error="grafanaOk = false"
      />
    </el-card>

    <!-- 告警列表 -->
    <el-card shadow="never">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>当前告警</span>
          <el-button size="small" @click="loadAlerts" :icon="Refresh">刷新</el-button>
        </div>
      </template>
      <el-empty v-if="!alerts.length" description="暂无告警，系统运行正常 ✓" />
      <div v-for="(alert, i) in alerts" :key="i" class="alert-item">
        <el-alert
          :title="alert.labels?.alertname || '未知告警'"
          :type="alert.labels?.severity === 'critical' ? 'error' : 'warning'"
          show-icon :closable="false"
        >
          <template #default>
            <div style="font-size:12px;color:#606266;margin-top:4px">
              {{ alert.annotations?.description || alert.annotations?.summary || '' }}
            </div>
            <div style="font-size:11px;color:#909399;margin-top:2px">
              实例: {{ alert.labels?.instance || '-' }} · 严重程度: {{ alert.labels?.severity || '-' }}
            </div>
          </template>
        </el-alert>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useLangStore } from '@/stores/lang'
import api from '@/api'

const overview = ref({ cpu_usage: null, mem_usage: null, disk_usage: null, load1: null })
const alerts = ref([])
const grafanaOk = ref(false)
const lang = useLangStore()
const servers = ref([])
const selectedInstance = ref('')  // 空字符串 = 本机
const instanceOnline = ref(true)
let timer = null

const grafanaExternal = `${location.protocol}//${location.hostname}:3000/grafana/`

// Grafana iframe URL：切换实例时传 var-instance 参数
const grafanaUrl = computed(() => {
  const base = `/grafana/d/autoops-overview/autoops-xi-tong-gai-lan?orgId=1&kiosk=tv&theme=light`
  if (selectedInstance.value) {
    return `${base}&var-instance=${encodeURIComponent(selectedInstance.value + ':9100')}`
  }
  return base
})

const metricCards = computed(() => [
  { label: 'CPU 使用率', value: overview.value.cpu_usage, unit: '%', color: '#3b82f6' },
  { label: '内存使用率', value: overview.value.mem_usage, unit: '%', color: '#10b981' },
  { label: '磁盘使用率', value: overview.value.disk_usage, unit: '%', color: '#f59e0b' },
  { label: '系统负载(1m)', value: overview.value.load1, unit: '', color: '#f56c6c' },
])

async function loadOverview() {
  const instance = selectedInstance.value
  try {
    const res = await api.get('/monitor/overview', {
      params: instance ? { instance: `${instance}:9100` } : {}
    })
    overview.value = res.data
    instanceOnline.value = Object.values(res.data).some(v => v !== null)
  } catch {
    overview.value = { cpu_usage: null, mem_usage: null, disk_usage: null, load1: null }
  }
}

async function loadAlerts() {
  try {
    const res = await api.get('/monitor/alerts')
    const all = Array.isArray(res.data) ? res.data : []
    alerts.value = all.filter(a => a.labels?.instance !== 'backend:8000')
  } catch {
    alerts.value = []
  }
}

function openGrafana() {
  window.open(grafanaExternal, '_blank')
}

watch(selectedInstance, () => {
  grafanaOk.value = false
  loadOverview()
})

onMounted(async () => {
  const res = await api.get('/servers')
  servers.value = res.data
  loadOverview()
  loadAlerts()
  timer = setInterval(() => { loadOverview(); loadAlerts() }, 15000)
})

onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.server-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 16px;
}
.metric-card { text-align: center; }
.metric-label { font-size: 13px; color: #909399; margin-bottom: 8px; }
.metric-value { font-size: 28px; font-weight: 700; }
.alert-item { margin-bottom: 8px; }
.grafana-placeholder {
  height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #64748b;
  gap: 8px;
}
</style>
