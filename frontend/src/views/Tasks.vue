<template>
  <div class="page-wrap">
    <el-row :gutter="16" style="height:100%">
      <!-- 左侧：执行任务 -->
      <el-col :span="9" style="height:100%;display:flex;flex-direction:column">

        <!-- 执行面板直接撑满整个左侧 -->
        <el-card shadow="never" style="flex:1;display:flex;flex-direction:column;min-height:0;overflow:hidden">
          <template #header><span style="font-weight:600">{{ lang.isZh ? '执行 Ansible 任务' : 'Run Ansible Task' }}</span></template>

          <div style="flex:1;display:flex;flex-direction:column;min-height:0;overflow:hidden">

            <!-- 固定区域：服务器 + 类型选择 -->
            <div style="flex-shrink:0;margin-bottom:4px">
              <el-form :model="taskForm" label-position="top">
                <el-form-item label="目标服务器" style="margin-bottom:10px">
                  <el-select v-model="taskForm.server_id" placeholder="选择服务器" style="width:100%">
                    <el-option v-for="s in servers" :key="s.id" :label="`${s.name} (${s.ip})`" :value="s.id">
                      <span>{{ s.name }}</span>
                      <span style="float:right;color:#94a3b8;font-size:12px">{{ s.ip }}</span>
                    </el-option>
                  </el-select>
                </el-form-item>
                <el-form-item label="任务类型" style="margin-bottom:10px">
                  <el-radio-group v-model="taskForm.task_type" @change="onTypeChange" style="width:100%;display:flex">
                    <el-radio-button value="shell" style="flex:1;text-align:center">Shell</el-radio-button>
                    <el-radio-button value="install" style="flex:1;text-align:center">安装包</el-radio-button>
                    <el-radio-button value="playbook" style="flex:1;text-align:center">Playbook</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </el-form>
            </div>

            <!-- 动态内容区：撑满剩余高度 -->
            <div style="flex:1;display:flex;flex-direction:column;min-height:0">

              <!-- Shell 命令 -->
              <template v-if="taskForm.task_type === 'shell'">
                <div style="flex:1;display:flex;flex-direction:column;min-height:0;gap:6px">
                  <div class="quick-cmds">
                    <el-tag v-for="q in quickCmds" :key="q.label" size="small" style="cursor:pointer" @click="taskForm.command = q.cmd">{{ q.label }}</el-tag>
                  </div>
                  <el-input
                    v-model="taskForm.command"
                    type="textarea"
                    class="fill-textarea"
                    placeholder="例如：df -h&#10;systemctl status nginx&#10;docker ps"
                    style="flex:1;font-family:monospace;font-size:13px"
                  />
                </div>
              </template>

              <!-- 安装软件包 -->
              <template v-if="taskForm.task_type === 'install'">
                <div style="flex:1;display:flex;flex-direction:column;gap:8px;overflow-y:auto">
                  <el-form :model="taskForm" label-position="top">
                    <el-form-item label="包管理器" style="margin-bottom:8px">
                      <el-radio-group v-model="taskForm.pkg_manager">
                        <el-radio value="auto">自动检测</el-radio>
                        <el-radio value="apt">apt</el-radio>
                        <el-radio value="yum">yum</el-radio>
                      </el-radio-group>
                    </el-form-item>
                    <el-form-item label="软件包名称（空格分隔）" style="margin-bottom:8px">
                      <el-input v-model="taskForm.packages" placeholder="例如：nginx git vim htop" />
                    </el-form-item>
                  </el-form>
                  <div class="quick-cmds">
                    <el-tag v-for="p in quickPkgs" :key="p" size="small" style="cursor:pointer" @click="addPkg(p)">{{ p }}</el-tag>
                  </div>
                </div>
              </template>

              <!-- 自定义 Playbook -->
              <template v-if="taskForm.task_type === 'playbook'">
                <div style="flex:1;display:flex;flex-direction:column;min-height:0;gap:6px">
                  <div style="font-size:12px;color:#94a3b8">Playbook YAML 内容：</div>
                  <el-input
                    v-model="taskForm.playbook_content"
                    type="textarea"
                    class="fill-textarea"
                    placeholder="---
- hosts: target
  become: yes
  gather_facts: yes
  tasks:
    - name: 示例任务
      shell: echo hello"
                    style="flex:1;font-family:monospace;font-size:12px"
                  />
                </div>
              </template>

            </div>
          </div>

          <!-- 执行按钮固定底部 -->
          <div style="padding:12px 0 0;border-top:1px solid #f1f5f9;flex-shrink:0;margin-top:10px">
            <el-button type="primary" :loading="running" @click="runTask" style="width:100%" :disabled="!taskForm.server_id">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" style="margin-right:6px">
                <polygon points="5 3 19 12 5 21 5 3" fill="currentColor"/>
              </svg>
              {{ lang.isZh ? '执行任务' : 'Run Task' }}
            </el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：任务列表 + 输出 -->
      <el-col :span="15" style="height:100%;display:flex;flex-direction:column;gap:12px">

        <!-- 任务列表固定高度 -->
        <el-card shadow="never" style="flex-shrink:0;height:300px;display:flex;flex-direction:column">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-weight:600">{{ lang.isZh ? '任务记录' : 'Task Records' }}</span>
              <div style="display:flex;gap:8px;align-items:center">
                <el-select v-model="filterServerId" placeholder="筛选服务器" clearable size="small" style="width:160px">
                  <el-option v-for="s in servers" :key="s.id" :label="s.name" :value="s.id" />
                </el-select>
                <el-button size="small" @click="loadTasks">刷新</el-button>
              </div>
            </div>
          </template>
          <div style="flex:1;overflow:hidden">
            <el-table :data="tasks" size="small" stripe height="100%" @row-click="selectTask" style="cursor:pointer">
            <el-table-column prop="id" label="ID" width="55" />
            <el-table-column label="类型" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="typeTagType(row.task_type)">{{ typeLabel(row.task_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="target_hosts" label="目标主机" show-overflow-tooltip />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="operator" label="操作人" width="80" />
            <el-table-column label="时间" width="100">
              <template #default="{ row }">{{ fmt(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          </div>
        </el-card>

        <!-- 任务输出撑满剩余高度 -->
        <el-card class="output-card" shadow="never" style="flex:1;display:flex;flex-direction:column;min-height:0">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-weight:600">
                执行输出
                <span v-if="selectedTask" style="font-weight:400;color:#94a3b8;font-size:12px;margin-left:8px">
                  #{{ selectedTask.id }} · {{ typeLabel(selectedTask.task_type) }}
                </span>
              </span>
              <el-tag v-if="selectedTask" :type="statusType(selectedTask.status)" size="small">
                {{ statusLabel(selectedTask.status) }}
              </el-tag>
            </div>
          </template>
          <div style="flex:1;overflow:hidden">
            <pre v-if="selectedTask?.output" class="output-box">{{ selectedTask.output }}</pre>
            <el-empty v-else description="点击任务记录查看输出" :image-size="60" />
          </div>
        </el-card>

      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useLangStore } from '@/stores/lang'
import api from '@/api'
import dayjs from 'dayjs'

const lang = useLangStore()

const servers = ref([])
const tasks = ref([])
const running = ref(false)
const selectedTask = ref(null)
const filterServerId = ref(null)

const taskForm = reactive({
  server_id: null,
  task_type: 'shell',
  command: '',
  packages: '',
  pkg_manager: 'auto',
  playbook_content: `---
- hosts: target
  become: yes
  gather_facts: yes
  tasks:
    - name: 示例：查看磁盘
      shell: df -h
      register: result
    - debug:
        msg: "{{ result.stdout }}"`,
})

const quickCmds = [
  { label: '磁盘使用', cmd: 'df -h' },
  { label: '内存使用', cmd: 'free -h' },
  { label: 'CPU信息', cmd: 'nproc && cat /proc/cpuinfo | grep "model name" | head -1' },
  { label: '系统信息', cmd: 'uname -a && cat /etc/os-release' },
  { label: 'Docker状态', cmd: 'docker ps && docker images' },
  { label: '进程列表', cmd: 'ps aux --sort=-%cpu | head -20' },
  { label: '网络连接', cmd: 'ss -tlnp' },
  { label: '系统日志', cmd: 'journalctl -n 50 --no-pager' },
]

const quickPkgs = ['nginx', 'git', 'vim', 'htop', 'curl', 'wget', 'unzip', 'python3', 'nodejs', 'docker.io']

function addPkg(pkg) {
  const cur = taskForm.packages.trim()
  if (!cur.split(/\s+/).includes(pkg)) {
    taskForm.packages = cur ? `${cur} ${pkg}` : pkg
  }
}

function onTypeChange() {
  // 切换类型时清空
}

function typeLabel(t) {
  return lang.t(t) || t
}
function typeTagType(t) {
  return { shell: 'primary', install: 'success', playbook: 'warning', init: 'info', ping: '', install_exporter: 'success' }[t] || ''
}
function statusType(s) {
  return { success: 'success', failed: 'danger', running: 'warning', pending: 'info' }[s] || 'info'
}
function statusLabel(s) { return lang.t(s) }
function fmt(t) { return t ? dayjs.tz(t).format('MM-DD HH:mm') : '-' }

async function loadTasks() {
  const params = filterServerId.value ? { server_id: filterServerId.value } : {}
  const res = await api.get('/tasks', { params })
  tasks.value = res.data
}

function selectTask(row) {
  selectedTask.value = row
  // 如果任务还在运行，轮询刷新
  if (row.status === 'running' || row.status === 'pending') {
    pollTask(row.id)
  }
}

async function pollTask(taskId) {
  const timer = setInterval(async () => {
    try {
      const res = await api.get(`/tasks/${taskId}`)
      const t = res.data
      // 更新列表中的任务
      const idx = tasks.value.findIndex(x => x.id === taskId)
      if (idx >= 0) tasks.value[idx] = t
      if (selectedTask.value?.id === taskId) selectedTask.value = t
      if (t.status !== 'running' && t.status !== 'pending') {
        clearInterval(timer)
      }
    } catch {
      clearInterval(timer)
    }
  }, 2000)
}

async function runTask() {
  if (!taskForm.server_id) return ElMessage.warning('请选择服务器')
  if (taskForm.task_type === 'shell' && !taskForm.command.trim()) return ElMessage.warning('请输入命令')
  if (taskForm.task_type === 'install' && !taskForm.packages.trim()) return ElMessage.warning('请输入软件包名称')

  running.value = true
  try {
    const res = await api.post('/tasks/run', {
      server_id: taskForm.server_id,
      task_type: taskForm.task_type,
      command: taskForm.command,
      packages: taskForm.packages,
      pkg_manager: taskForm.pkg_manager,
      playbook_content: taskForm.playbook_content,
    })
    ElMessage.success(`任务已提交，ID: ${res.data.id}`)
    tasks.value.unshift(res.data)
    selectedTask.value = res.data
    pollTask(res.data.id)
  } finally {
    running.value = false
  }
}

watch(filterServerId, loadTasks)

onMounted(async () => {
  const res = await api.get('/servers')
  servers.value = res.data
  loadTasks()
})
</script>

<style scoped>
.page-wrap { height: calc(100vh - 120px); }
.quick-cmds {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  flex-shrink: 0;
}

/* textarea 撑满父容器 */
.fill-textarea { display: flex; flex-direction: column; }
:deep(.fill-textarea .el-textarea__inner) {
  flex: 1;
  height: 100% !important;
  resize: none;
  min-height: 80px;
}
.output-box {
  background: #0f172a;
  color: #e2e8f0;
  padding: 14px;
  border-radius: 8px;
  height: 100%;
  overflow-y: auto;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Consolas', 'Monaco', monospace;
  margin: 0;
}
:deep(.el-card__body) { padding: 16px !important; }
/* 左侧执行卡片 body 需要 flex */
.el-col:first-child :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px !important;
}
/* 右侧输出卡片 body */
.output-card :deep(.el-card__body) {
  padding: 16px !important;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
