<template>
  <div class="page-wrap">
    <el-row :gutter="16" style="height:100%">
      <!-- 左侧 -->
      <el-col :span="8" style="height:100%;display:flex;flex-direction:column;gap:12px">

        <!-- 手动触发部署：内容自然高度，无滚动条 -->
        <el-card shadow="never" style="flex-shrink:0">
          <template #header><span style="font-weight:600">{{ lang.isZh ? '手动触发部署' : 'Manual Deploy' }}</span></template>
          <el-form :model="deployForm" label-position="top">
            <el-form-item :label="lang.isZh ? '选择应用' : 'Application'" style="margin-bottom:14px">
              <el-select v-model="deployForm.app_id" :placeholder="lang.isZh ? '请选择应用' : 'Select app'" style="width:100%" @change="deployForm.server_id = null">
                <el-option v-for="a in apps" :key="a.id" :label="a.name" :value="a.id">
                  <span>{{ a.name }}</span>
                  <el-tag size="small" :type="a.source_type === 'git' ? 'primary' : 'warning'" style="margin-left:6px">{{ a.source_type }}</el-tag>
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item :label="lang.isZh ? '目标服务器' : 'Target Server'" style="margin-bottom:14px">
              <el-select v-model="deployForm.server_id" :placeholder="lang.isZh ? '选择部署目标服务器' : 'Select server'" style="width:100%">
                <el-option v-for="s in servers" :key="s.id" :label="`${s.name} (${s.ip})`" :value="s.id">
                  <span :style="{ color: s.status === 'online' ? '#16a34a' : '#94a3b8' }">●</span>
                  {{ s.name }} ({{ s.ip }})
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item :label="lang.isZh ? '版本 / 分支' : 'Version / Branch'" style="margin-bottom:16px">
              <el-input v-model="deployForm.version" :placeholder="lang.isZh ? '留空使用应用默认分支' : 'Leave empty for default branch'" />
            </el-form-item>
            <el-button type="primary" :loading="previewing" @click="showPreview" style="width:100%" :disabled="!deployForm.app_id || !deployForm.server_id">
              <el-icon><Promotion /></el-icon>&nbsp;{{ lang.isZh ? '预览并部署' : 'Preview & Deploy' }}
            </el-button>
          </el-form>
        </el-card>

        <!-- 版本回滚：内容自然高度 -->
        <el-card shadow="never" style="flex-shrink:0">
          <template #header><span style="font-weight:600">{{ lang.isZh ? '版本回滚' : 'Rollback' }}</span></template>
          <el-form :model="rollbackForm" label-position="top">
            <el-form-item :label="lang.isZh ? '部署记录 ID' : 'Record ID'" style="margin-bottom:6px">
              <el-input-number v-model="rollbackForm.record_id" :min="1" controls-position="right" style="width:100%" />
            </el-form-item>
            <div style="font-size:12px;color:#94a3b8;margin-bottom:14px">
              {{ lang.isZh ? '从右侧找到成功的记录ID填入' : 'Enter a successful record ID from the right' }}
            </div>
            <el-button type="warning" @click="doRollback" style="width:100%">
              <el-icon><RefreshLeft /></el-icon>&nbsp;{{ lang.isZh ? '回滚到此版本' : 'Rollback' }}
            </el-button>
          </el-form>
        </el-card>

        <!-- 撑满剩余空间，让左侧底部和右侧对齐 -->
        <div style="flex:1"></div>
      </el-col>

            <!-- 右侧：部署记录 -->
      <el-col :span="16" style="height:100%;display:flex;flex-direction:column">
        <el-card shadow="never" style="flex:1;display:flex;flex-direction:column;min-height:0">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span>{{ lang.isZh ? '部署记录' : 'Deploy Records' }}</span>
              <div style="display:flex;gap:8px;align-items:center">
                <el-select v-model="filterAppId" :placeholder="lang.isZh ? '筛选应用' : 'Filter app'" clearable size="small" style="width:160px">
                  <el-option v-for="a in apps" :key="a.id" :label="a.name" :value="a.id" />
                </el-select>
                <el-button size="small" @click="loadRecords" :icon="Refresh">{{ lang.isZh ? '刷新' : 'Refresh' }}</el-button>
              </div>
            </div>
          </template>
          <div style="flex:1;overflow:hidden">
            <el-table :data="records" v-loading="loading" stripe size="small" height="100%">
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column :label="lang.isZh ? '应用' : 'App'" width="120">
                <template #default="{ row }">{{ appName(row.app_id) }}</template>
              </el-table-column>
              <el-table-column prop="version" :label="lang.isZh ? '版本' : 'Version'" show-overflow-tooltip />
              <el-table-column :label="lang.isZh ? '触发' : 'Trigger'" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.trigger === 'ci' ? 'success' : 'info'" size="small">
                    {{ lang.t(row.trigger) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column :label="lang.isZh ? '状态' : 'Status'" width="90">
                <template #default="{ row }">
                  <el-tag :type="statusType(row.status)" size="small">{{ lang.t(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="operator" :label="lang.isZh ? '操作人' : 'Operator'" width="90" />
              <el-table-column :label="lang.isZh ? '时间' : 'Time'" width="110">
                <template #default="{ row }">{{ fmt(row.created_at) }}</template>
              </el-table-column>
              <el-table-column :label="lang.isZh ? '操作' : 'Action'" width="70">
                <template #default="{ row }">
                  <el-button size="small" @click="viewLog(row)">{{ lang.isZh ? '日志' : 'Log' }}</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 部署日志对话框 -->
    <el-dialog v-model="logDialog" :title="`${lang.isZh ? '部署日志' : 'Deploy Log'} #${currentRecord?.id}`" width="800px">
      <div style="margin-bottom:8px;display:flex;align-items:center;gap:8px">
        <el-tag :type="statusType(currentRecord?.status)" size="small">{{ lang.t(currentRecord?.status) }}</el-tag>
        <span style="font-size:12px;color:#909399">{{ lang.isZh ? '实时推送' : 'Live stream' }}</span>
      </div>
      <pre class="log-box" ref="logBox">{{ liveLog }}</pre>
    </el-dialog>

    <!-- 部署预览确认弹窗 -->
    <el-dialog v-model="previewVisible" :title="lang.isZh ? '部署预览确认' : 'Deploy Preview'" width="520px">
      <div v-if="previewData">
        <el-alert v-if="previewData.is_deploying" type="warning" :title="previewData.warning" :closable="false" style="margin-bottom:12px" />
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
          <el-descriptions-item :label="lang.isZh ? '应用' : 'App'">{{ previewData.app?.name }}</el-descriptions-item>
          <el-descriptions-item :label="lang.isZh ? '来源' : 'Source'">{{ previewData.app?.source_type }}</el-descriptions-item>
          <el-descriptions-item :label="lang.isZh ? '目标服务器' : 'Server'">{{ previewData.server?.name }} ({{ previewData.server?.ip }})</el-descriptions-item>
          <el-descriptions-item :label="lang.isZh ? '部署路径' : 'Path'">{{ previewData.app?.deploy_path }}/{{ previewData.app?.name }}</el-descriptions-item>
        </el-descriptions>
        <div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:8px">
          {{ lang.isZh ? '将执行以下步骤：' : 'Steps to execute:' }}
        </div>
        <div v-for="(step, i) in previewData.steps" :key="i" class="preview-step">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="flex-shrink:0;color:#3b82f6">
            <polyline points="9 11 12 14 22 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span>{{ step }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">{{ lang.isZh ? '取消' : 'Cancel' }}</el-button>
        <el-button type="primary" :loading="deploying" @click="confirmDeploy" :disabled="previewData?.is_deploying">
          {{ lang.isZh ? '确认部署' : 'Confirm Deploy' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, nextTick } from 'vue'
import { Refresh, Promotion, RefreshLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useLangStore } from '@/stores/lang'
import api from '@/api'
import dayjs from 'dayjs'

const lang = useLangStore()
const apps = ref([])
const servers = ref([])
const records = ref([])
const loading = ref(false)
const deploying = ref(false)
const previewing = ref(false)
const previewVisible = ref(false)
const previewData = ref(null)
const filterAppId = ref(null)
const logDialog = ref(false)
const currentRecord = ref(null)
const liveLog = ref('')
const logBox = ref()
let ws = null

const deployForm = reactive({ app_id: null, server_id: null, version: '' })
const rollbackForm = reactive({ record_id: null })

function appName(id) { return apps.value.find(a => a.id === id)?.name || id }
function statusType(s) {
  return { success: 'success', failed: 'danger', running: 'warning', pending: 'info' }[s] || 'info'
}
function fmt(t) { return t ? dayjs.tz(t).format('MM-DD HH:mm') : '-' }

async function loadRecords() {
  loading.value = true
  try {
    const params = filterAppId.value ? { app_id: filterAppId.value } : {}
    const res = await api.get('/deploy/records', { params })
    records.value = res.data
  } finally {
    loading.value = false
  }
}

async function triggerDeploy() {
  if (!deployForm.app_id) return ElMessage.warning(lang.isZh ? '请选择应用' : 'Please select an app')
  if (!deployForm.server_id) return ElMessage.warning(lang.isZh ? '请选择目标服务器' : 'Please select a server')
  deploying.value = true
  try {
    const res = await api.post('/deploy/trigger', deployForm)
    ElMessage.success(`${lang.isZh ? '部署已触发，记录ID' : 'Deploy triggered, ID'}: ${res.data.id}`)
    previewVisible.value = false
    loadRecords()
    viewLog(res.data)
  } finally {
    deploying.value = false
  }
}

async function showPreview() {
  if (!deployForm.app_id || !deployForm.server_id) return
  previewing.value = true
  try {
    const res = await api.get(`/deploy/preview/${deployForm.app_id}`, {
      params: { server_id: deployForm.server_id }
    })
    previewData.value = res.data
    previewVisible.value = true
  } finally {
    previewing.value = false
  }
}

async function confirmDeploy() {
  await triggerDeploy()
}

async function doRollback() {
  if (!rollbackForm.record_id) return ElMessage.warning(lang.isZh ? '请输入记录ID' : 'Please enter record ID')
  const res = await api.post('/deploy/rollback', rollbackForm)
  ElMessage.success(`${lang.isZh ? '回滚任务已提交，记录ID' : 'Rollback submitted, ID'}: ${res.data.id}`)
  loadRecords()
  viewLog(res.data)
}

function viewLog(record) {
  currentRecord.value = record
  liveLog.value = record.log || ''
  logDialog.value = true
  if (ws) ws.close()
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/ws/${record.id}`)
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data)
    currentRecord.value.status = data.status
    liveLog.value = data.log
    nextTick(() => { if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight })
    if (['success', 'failed'].includes(data.status)) ws.close()
  }
}

watch(logDialog, (v) => { if (!v && ws) { ws.close(); ws = null } })
watch(filterAppId, loadRecords)

onMounted(async () => {
  const [appsRes, serversRes] = await Promise.all([api.get('/apps'), api.get('/servers')])
  apps.value = appsRes.data
  servers.value = serversRes.data
  loadRecords()
})
</script>

<style scoped>
.page-wrap { height: calc(100vh - 120px); }
.log-box {
  background: #1e1e1e; color: #d4d4d4;
  padding: 12px; border-radius: 4px;
  height: 480px; overflow-y: auto;
  font-size: 12px; line-height: 1.6;
  white-space: pre-wrap; word-break: break-all;
}
.preview-step {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13px;
  color: #374151;
  margin-bottom: 4px;
  background: #f8fafc;
}
:deep(.el-card__body) { padding: 16px !important; }
.el-col:last-child :deep(.el-card__body) {
  flex: 1; display: flex; flex-direction: column;
  overflow: hidden; padding: 0 !important;
}
</style>
