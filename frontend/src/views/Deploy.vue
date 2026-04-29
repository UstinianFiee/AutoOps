<template>
  <div class="page-wrap">
    <el-row :gutter="16" style="height:100%">
      <!-- 左侧 -->
      <el-col :span="8" style="height:100%;display:flex;flex-direction:column;gap:12px">

        <el-card shadow="never" style="flex-shrink:0">
          <template #header><span style="font-weight:600">{{ lang.isZh ? '手动触发部署' : 'Manual Deploy' }}</span></template>
          <el-form :model="deployForm" label-position="top">
            <el-form-item :label="lang.isZh ? '选择应用' : 'Application'">
              <el-select v-model="deployForm.app_id" :placeholder="lang.isZh ? '请选择应用' : 'Select app'" style="width:100%">
                <el-option v-for="a in apps" :key="a.id" :label="a.name" :value="a.id" />
              </el-select>
            </el-form-item>
            <el-form-item :label="lang.isZh ? '版本 / 分支' : 'Version / Branch'">
              <el-input v-model="deployForm.version" :placeholder="lang.isZh ? '留空使用应用默认分支' : 'Leave empty for default branch'" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="deploying" @click="triggerDeploy" style="width:100%">
                <el-icon><Promotion /></el-icon>&nbsp;{{ lang.isZh ? '立即部署' : 'Deploy Now' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never" style="flex-shrink:0">
          <template #header><span style="font-weight:600">{{ lang.isZh ? '版本回滚' : 'Rollback' }}</span></template>
          <el-form :model="rollbackForm" label-position="top">
            <el-form-item :label="lang.isZh ? '部署记录 ID' : 'Record ID'">
              <el-input-number v-model="rollbackForm.record_id" :min="1" controls-position="right" style="width:100%" />
            </el-form-item>
            <el-form-item>
              <el-button type="warning" @click="doRollback" style="width:100%">
                <el-icon><RefreshLeft /></el-icon>&nbsp;{{ lang.isZh ? '回滚到此版本' : 'Rollback' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 占位撑满，让左侧和右侧底部对齐 -->
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
const records = ref([])
const loading = ref(false)
const deploying = ref(false)
const filterAppId = ref(null)
const logDialog = ref(false)
const currentRecord = ref(null)
const liveLog = ref('')
const logBox = ref()
let ws = null

const deployForm = reactive({ app_id: null, version: '' })
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
  deploying.value = true
  try {
    const res = await api.post('/deploy/trigger', deployForm)
    ElMessage.success(`${lang.isZh ? '部署已触发，记录ID' : 'Deploy triggered, ID'}: ${res.data.id}`)
    loadRecords()
    viewLog(res.data)
  } finally {
    deploying.value = false
  }
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
  const res = await api.get('/apps')
  apps.value = res.data
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
/* 右侧部署记录卡片 body 需要 flex */
:deep(.el-card__body) { padding: 16px !important; }
.el-col:last-child :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0 !important;
}
</style>
