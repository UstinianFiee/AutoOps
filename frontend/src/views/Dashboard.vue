<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6" v-for="card in statCards" :key="card.label">
        <div class="stat-card">
          <div class="stat-icon-wrap" :style="{ background: card.bg }">
            <span v-html="card.icon" :style="{ color: card.color }"></span>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ card.value }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
          <div class="stat-sub" :style="{ color: card.color }">{{ card.sub }}</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px;height:calc(100vh - 240px)">
      <!-- 最近部署 -->
      <el-col :span="16" style="height:100%">
        <el-card shadow="never" style="height:100%;display:flex;flex-direction:column">
          <template #header>
            <div class="card-header">
              <span>最近部署记录</span>
              <router-link to="/deploy" class="view-all">查看全部 →</router-link>
            </div>
          </template>
          <div style="flex:1;overflow:hidden">
            <el-table :data="stats.recent_deploys" size="small" height="100%">
              <el-table-column label="应用" width="120">
                <template #default="{ row }">
                  <span class="app-name-cell">{{ row.app_id }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="version" label="版本" />
              <el-table-column prop="trigger" label="触发" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.trigger === 'ci' ? 'success' : 'primary'" size="small">
                    {{ row.trigger === 'ci' ? 'CI' : '手动' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="operator" label="操作人" width="90" />
              <el-table-column label="时间">
                <template #default="{ row }">
                  <span class="time-cell">{{ fmt(row.created_at) }}</span>
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="!stats.recent_deploys?.length" description="暂无部署记录" :image-size="60" />
          </div>
        </el-card>
      </el-col>

      <!-- 最近任务 -->
      <el-col :span="8" style="height:100%">
        <el-card shadow="never" style="height:100%;display:flex;flex-direction:column">
          <template #header>
            <span>Ansible 任务</span>
          </template>
          <div class="task-list" style="flex:1;overflow-y:auto">
            <div v-for="task in tasks" :key="task.id" class="task-item" @click="showTaskDetail(task)" style="cursor:pointer">
              <div class="task-dot" :class="task.status"></div>
              <div class="task-info">
                <div class="task-type">
                  {{ taskTypeLabel(task.task_type) }}
                  <el-tag size="small" :type="taskStatusType(task.status)" style="margin-left:4px">
                    {{ taskStatusLabel(task.status) }}
                  </el-tag>
                </div>
                <div class="task-host">{{ task.target_hosts }}</div>
              </div>
              <div class="task-time">{{ fmt(task.created_at) }}</div>
            </div>
            <el-empty v-if="!tasks.length" description="暂无任务" :image-size="50" />
          </div>
        </el-card>
      </el-col>
    </el-row>
    <!-- 任务详情弹窗 -->
    <el-dialog v-model="taskDetailVisible" title="任务详情" width="700px">
      <div v-if="selectedTask">
        <el-descriptions :column="2" border size="small" style="margin-bottom:12px">
          <el-descriptions-item label="任务类型">{{ taskTypeLabel(selectedTask.task_type) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="taskStatusType(selectedTask.status)" size="small">{{ taskStatusLabel(selectedTask.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="目标主机">{{ selectedTask.target_hosts }}</el-descriptions-item>
          <el-descriptions-item label="操作人">{{ selectedTask.operator }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ fmt(selectedTask.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ selectedTask.finished_at ? fmt(selectedTask.finished_at) : '-' }}</el-descriptions-item>
        </el-descriptions>
        <div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:8px">执行输出</div>
        <pre class="task-output">{{ selectedTask.output || '暂无输出' }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useLangStore } from '@/stores/lang'
import api from '@/api'
import dayjs from 'dayjs'

const lang = useLangStore()
const stats = ref({
  total_servers: 0, online_servers: 0,
  total_apps: 0, running_apps: 0,
  total_deploys: 0, success_deploys: 0,
  recent_deploys: [],
})
const tasks = ref([])

const statCards = computed(() => [
  {
    label: '服务器总数', value: stats.value.total_servers,
    sub: `在线 ${stats.value.online_servers} 台`,
    color: '#3b82f6', bg: '#eff6ff',
    icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><rect x="2" y="2" width="20" height="8" rx="2" stroke="currentColor" stroke-width="1.8"/><rect x="2" y="14" width="20" height="8" rx="2" stroke="currentColor" stroke-width="1.8"/><circle cx="6" cy="6" r="1.2" fill="currentColor"/><circle cx="6" cy="18" r="1.2" fill="currentColor"/></svg>`,
  },
  {
    label: '应用总数', value: stats.value.total_apps,
    sub: `运行中 ${stats.value.running_apps} 个`,
    color: '#10b981', bg: '#f0fdf4',
    icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  },
  {
    label: '部署总次数', value: stats.value.total_deploys,
    sub: `成功 ${stats.value.success_deploys} 次`,
    color: '#f59e0b', bg: '#fffbeb',
    icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><polyline points="22 4 12 14.01 9 11.01" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  },
  {
    label: '部署成功率',
    value: stats.value.total_deploys ? Math.round((stats.value.success_deploys / stats.value.total_deploys) * 100) + '%' : '-',
    sub: '近期统计',
    color: '#8b5cf6', bg: '#f5f3ff',
    icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  },
])

const taskDetailVisible = ref(false)
const selectedTask = ref(null)

function showTaskDetail(task) {
  selectedTask.value = task
  taskDetailVisible.value = true
}

function taskTypeLabel(t) { return lang.t(t) }
function taskStatusType(s) {
  return { success: 'success', failed: 'danger', running: 'warning', pending: 'info' }[s] || 'info'
}
function taskStatusLabel(s) { return lang.t(s) }

function statusType(s) {
  return { success: 'success', failed: 'danger', running: 'warning', pending: 'info' }[s] || 'info'
}
function statusLabel(s) { return lang.t(s) }
function fmt(t) { return t ? dayjs.tz(t).format('MM-DD HH:mm') : '-' }

async function load() {
  const [s, t] = await Promise.all([api.get('/dashboard/stats'), api.get('/dashboard/tasks')])
  stats.value = s.data
  tasks.value = t.data
}
onMounted(load)
</script>

<style scoped>
.dashboard {}

/* 统计卡片 */
.stat-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  gap: 4px 16px;
  align-items: center;
  transition: box-shadow 0.2s;
}
.stat-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.07); }
.stat-icon-wrap {
  width: 48px; height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  grid-row: 1 / 3;
}
.stat-value { font-size: 28px; font-weight: 700; color: #0f172a; line-height: 1; }
.stat-label { font-size: 13px; color: #64748b; margin-top: 2px; }
.stat-sub { grid-column: 2; font-size: 12px; font-weight: 500; }

/* 卡片头 */
.card-header { display: flex; justify-content: space-between; align-items: center; }
.view-all { font-size: 13px; color: #3b82f6; text-decoration: none; }
.view-all:hover { text-decoration: underline; }

.app-name-cell { font-weight: 500; color: #374151; }
.time-cell { color: #94a3b8; font-size: 12px; }

/* 任务列表 */
.task-list { display: flex; flex-direction: column; gap: 12px; padding-right: 4px; }
.task-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  transition: background 0.15s;
}
.task-item:hover { background: #eff6ff; }
.task-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.task-dot.success { background: #22c55e; }
.task-dot.failed  { background: #ef4444; }
.task-dot.running { background: #f59e0b; }
.task-dot.pending { background: #94a3b8; }
.task-info { flex: 1; min-width: 0; }
.task-type { font-size: 13px; font-weight: 500; color: #374151; display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.task-host { font-size: 12px; color: #94a3b8; margin-top: 1px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-time { font-size: 11px; color: #94a3b8; white-space: nowrap; }
.task-output {
  background: #1e1e1e; color: #d4d4d4;
  padding: 12px; border-radius: 6px;
  max-height: 400px; overflow-y: auto;
  font-size: 12px; line-height: 1.6;
  white-space: pre-wrap; word-break: break-all;
}
:deep(.el-card__body) { padding: 16px !important; }
</style>
