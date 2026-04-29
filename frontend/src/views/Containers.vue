<template>
  <div class="page-wrap">
    <!-- 服务器选择器 -->
    <div class="server-bar">
      <span style="font-size:13px;color:#64748b;margin-right:8px;white-space:nowrap">管理服务器：</span>
      <el-radio-group v-model="selectedServerId" @change="onServerChange" size="small">
        <el-radio-button :value="null">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:4px">
            <rect x="2" y="2" width="20" height="8" rx="2" stroke="currentColor" stroke-width="2"/>
            <rect x="2" y="14" width="20" height="8" rx="2" stroke="currentColor" stroke-width="2"/>
          </svg>
          AutoOps 本机
        </el-radio-button>
        <el-radio-button v-for="s in servers" :key="s.id" :value="s.id">
          <span :style="{ color: s.status === 'online' ? '#16a34a' : '#94a3b8' }">●</span>
          {{ s.name }} ({{ s.ip }})
        </el-radio-button>
      </el-radio-group>
      <el-button
        v-if="selectedServerId"
        size="small"
        type="success"
        style="margin-left:auto"
        @click="installExporter"
        :loading="installingExporter"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:4px">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        安装监控 (node_exporter)
      </el-button>
    </div>

    <el-tabs v-model="activeTab" class="tabs-wrap">
      <!-- 容器列表 -->
      <el-tab-pane label="容器列表" name="containers">
        <div class="tab-content">
          <div class="toolbar">
            <el-button @click="load" :icon="Refresh">刷新</el-button>
            <el-switch
              v-if="!selectedServerId"
              v-model="showAll"
              active-text="全部"
              inactive-text="运行中"
              @change="load"
              style="margin-left: 12px"
            />
          </div>
          <div class="table-wrap">
            <el-table :data="containers" v-loading="loading" stripe height="100%">
              <el-table-column prop="name" label="容器名" min-width="160" show-overflow-tooltip />
              <el-table-column prop="image" label="镜像" min-width="180" show-overflow-tooltip />
              <el-table-column prop="status" label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'running' ? 'success' : 'info'" size="small">
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" min-width="260">
                <template #default="{ row }">
                  <div class="action-btns">
                    <el-button size="small" type="success" @click="startContainer(row)" :disabled="row.status === 'running'">启动</el-button>
                    <el-button size="small" type="warning" @click="stopContainer(row)" :disabled="row.status !== 'running'">停止</el-button>
                    <el-button size="small" @click="restartContainer(row)">重启</el-button>
                    <el-button size="small" type="primary" @click="viewLogs(row)">日志</el-button>
                    <el-button size="small" type="danger" @click="removeContainer(row)">删除</el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-tab-pane>

      <!-- 镜像管理 -->
      <el-tab-pane label="镜像管理" name="images">
        <div class="tab-content">
          <div class="toolbar">
            <el-button type="primary" :icon="Download" @click="pullImageDialog = true">拉取镜像</el-button>
            <el-button @click="loadImages" :icon="Refresh" style="margin-left:8px">刷新</el-button>
          </div>
          <div class="table-wrap">
            <el-table :data="images" v-loading="loadingImages" stripe height="100%">
              <el-table-column prop="id" label="ID" width="110" show-overflow-tooltip />
              <el-table-column label="标签" min-width="200">
                <template #default="{ row }">
                  <el-tag v-for="tag in row.tags" :key="tag" size="small" style="margin-right:4px;margin-bottom:2px">{{ tag }}</el-tag>
                  <span v-if="!row.tags.length" style="color:#909399">无标签</span>
                </template>
              </el-table-column>
              <el-table-column prop="size_mb" label="大小" width="100" />
              <el-table-column label="操作" width="80">
                <template #default="{ row }">
                  <el-button size="small" type="danger" @click="removeImage(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 日志对话框 -->
    <el-dialog v-model="logDialog" title="容器日志" width="860px">
      <pre class="log-content">{{ logs }}</pre>
    </el-dialog>

    <!-- 拉取镜像对话框 -->
    <el-dialog v-model="pullImageDialog" title="拉取镜像" width="520px" :close-on-click-modal="!pulling">
      <el-input
        v-model="pullImageName"
        placeholder="例如: nginx:latest"
        :disabled="pulling"
        @keyup.enter="pullImage"
      />

      <!-- 进度展示区 -->
      <div v-if="pulling || pullLogs.length" class="pull-log-wrap">
        <div class="pull-log-box" ref="pullLogBox">
          <div
            v-for="(line, i) in pullLogs"
            :key="i"
            :class="['pull-log-line', line.type]"
          >{{ line.text }}</div>
        </div>
        <!-- 总进度条（本机 Docker SDK 才有百分比） -->
        <el-progress
          v-if="pullPercent > 0"
          :percentage="pullPercent"
          :status="pullPercent >= 100 ? 'success' : undefined"
          style="margin-top:8px"
        />
      </div>

      <template #footer>
        <el-button @click="closePullDialog" :disabled="pulling">取消</el-button>
        <el-button type="primary" @click="pullImage" :loading="pulling" :disabled="pulling">
          {{ pulling ? '拉取中...' : '拉取' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { Refresh, Download } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useLangStore } from '@/stores/lang'
import api from '@/api'

const activeTab = ref('containers')
const containers = ref([])
const images = ref([])
const lang = useLangStore()
const servers = ref([])
const loading = ref(false)
const loadingImages = ref(false)
const showAll = ref(true)
const logDialog = ref(false)
const logs = ref('')
const pullImageDialog = ref(false)
const pullImageName = ref('')
const pulling = ref(false)
const pullLogs = ref([])
const pullPercent = ref(0)
const pullLogBox = ref(null)
const selectedServerId = ref(null)
const installingExporter = ref(false)

// 当前服务器的 query 参数
const serverQuery = () => selectedServerId.value ? { server_id: selectedServerId.value } : {}

function onServerChange() {
  load()
  loadImages()
}

async function load() {
  loading.value = true
  try {
    const params = selectedServerId.value
      ? { server_id: selectedServerId.value }
      : { all: showAll.value }
    const res = await api.get('/containers', { params })
    containers.value = res.data
  } catch (e) {
    containers.value = []
  } finally {
    loading.value = false
  }
}

async function loadImages() {
  loadingImages.value = true
  try {
    const res = await api.get('/containers/images/list', { params: serverQuery() })
    images.value = res.data
  } catch {
    images.value = []
  } finally {
    loadingImages.value = false
  }
}

async function installExporter() {
  if (!selectedServerId.value) return
  await ElMessageBox.confirm('将在该服务器安装 node_exporter 并加入 Prometheus 监控，确认？', '安装监控', { type: 'info' })
  installingExporter.value = true
  try {
    const res = await api.post(`/servers/${selectedServerId.value}/install-exporter`)
    ElMessage.success(`安装任务已提交，任务ID: ${res.data.task_id}，可在 Ansible 任务页查看进度`)
  } finally {
    installingExporter.value = false
  }
}

async function startContainer(row) {
  await api.post(`/containers/${row.id}/start`, null, { params: serverQuery() })
  ElMessage.success('启动成功')
  load()
}
async function stopContainer(row) {
  await api.post(`/containers/${row.id}/stop`, null, { params: serverQuery() })
  ElMessage.success('停止成功')
  load()
}
async function restartContainer(row) {
  await api.post(`/containers/${row.id}/restart`, null, { params: serverQuery() })
  ElMessage.success('重启成功')
  load()
}
async function removeContainer(row) {
  await ElMessageBox.confirm(`确认删除容器 ${row.name}？`, '确认', { type: 'warning' })
  await api.delete(`/containers/${row.id}`, { params: { force: true, ...serverQuery() } })
  ElMessage.success('删除成功')
  load()
}
async function viewLogs(row) {
  const res = await api.get(`/containers/${row.id}/logs`, { params: serverQuery() })
  logs.value = res.data.logs
  logDialog.value = true
}
async function removeImage(row) {
  await ElMessageBox.confirm(`确认删除镜像 ${row.id}？`, '确认', { type: 'warning' })
  await api.delete(`/containers/images/${row.id}`, { params: { force: true, ...serverQuery() } })
  ElMessage.success('删除成功')
  loadImages()
}
async function pullImage() {
  if (!pullImageName.value) return ElMessage.warning('请输入镜像名称')
  pulling.value = true
  pullLogs.value = []
  pullPercent.value = 0

  const token = localStorage.getItem('token') || sessionStorage.getItem('token') || ''
  const baseURL = api.defaults?.baseURL || '/api'
  const serverParam = selectedServerId.value ? `&server_id=${selectedServerId.value}` : ''
  const url = `${baseURL}/containers/images/pull-stream?image=${encodeURIComponent(pullImageName.value)}${serverParam}`

  try {
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!response.ok) {
      const err = await response.text()
      throw new Error(err || `HTTP ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const parts = buf.split('\n\n')
      buf = parts.pop()
      for (const part of parts) {
        const line = part.replace(/^data:\s*/, '').trim()
        if (!line) continue
        try {
          const msg = JSON.parse(line)
          if (msg.type === 'progress') {
            // 更新或追加日志行（按 layer 去重，只保留最新状态）
            if (msg.layer) {
              const idx = pullLogs.value.findIndex(l => l.layer === msg.layer)
              if (idx >= 0) {
                pullLogs.value[idx] = { ...msg, type: 'progress' }
              } else {
                pullLogs.value.push({ ...msg, type: 'progress' })
              }
            } else {
              pullLogs.value.push({ text: msg.text, type: 'progress' })
            }
            if (msg.percent) pullPercent.value = msg.percent
          } else if (msg.type === 'done') {
            pullPercent.value = 100
            pullLogs.value.push({ text: msg.text, type: 'done' })
            ElMessage.success(msg.text)
            pulling.value = false
            pullImageName.value = ''
            loadImages()
          } else if (msg.type === 'error') {
            pullLogs.value.push({ text: msg.text, type: 'error' })
            ElMessage.error(msg.text)
            pulling.value = false
          }
          // 自动滚动到底部
          await nextTick()
          if (pullLogBox.value) {
            pullLogBox.value.scrollTop = pullLogBox.value.scrollHeight
          }
        } catch {}
      }
    }
  } catch (e) {
    pullLogs.value.push({ text: String(e), type: 'error' })
    ElMessage.error('拉取失败: ' + e.message)
  } finally {
    pulling.value = false
  }
}

function closePullDialog() {
  if (pulling.value) return
  pullImageDialog.value = false
  pullLogs.value = []
  pullPercent.value = 0
  pullImageName.value = ''
}

onMounted(async () => {
  const res = await api.get('/servers')
  servers.value = res.data
  load()
  loadImages()
})
</script>

<style scoped>
.page-wrap {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  gap: 10px;
}

.server-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 16px;
  flex-shrink: 0;
}

.tabs-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
:deep(.el-tabs__content) { flex: 1; overflow: hidden; padding: 0; }
:deep(.el-tab-pane) { height: 100%; }

.tab-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 10px;
  padding-top: 12px;
}
.toolbar { display: flex; align-items: center; flex-shrink: 0; }
.table-wrap {
  flex: 1;
  overflow: hidden;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
}
.action-btns { display: flex; align-items: center; gap: 4px; }
.log-content {
  background: #1e1e1e; color: #d4d4d4;
  padding: 12px; border-radius: 4px;
  max-height: 500px; overflow-y: auto;
  font-size: 12px; line-height: 1.5;
  white-space: pre-wrap; word-break: break-all;
}

.pull-log-wrap {
  margin-top: 12px;
}
.pull-log-box {
  background: #0f172a;
  border-radius: 8px;
  padding: 10px 12px;
  max-height: 260px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.6;
}
.pull-log-line {
  white-space: pre-wrap;
  word-break: break-all;
  color: #94a3b8;
}
.pull-log-line.done {
  color: #4ade80;
  font-weight: 600;
}
.pull-log-line.error {
  color: #f87171;
}
</style>
