<template>
  <div class="page-wrap">
    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="openDialog()">添加服务器</el-button>
      <el-input v-model="search" placeholder="搜索名称/IP" clearable style="width: 240px; margin-left: 12px" />
    </div>

    <div class="table-wrap">
      <el-table :data="filtered" v-loading="loading" stripe height="100%">
        <el-table-column prop="name" label="名称" min-width="100" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP地址" min-width="130" show-overflow-tooltip />
        <el-table-column prop="port" label="端口" width="65" />
        <el-table-column prop="group" label="分组" width="80" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="75">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'online' ? 'success' : row.status === 'offline' ? 'danger' : 'warning'"
              size="small"
            >
              {{ lang.t(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="os_info" label="系统" min-width="100" show-overflow-tooltip />
        <el-table-column label="配置" width="90">
          <template #default="{ row }">
            <span v-if="row.cpu_cores">{{ row.cpu_cores }}核 {{ row.memory_gb }}G</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="280">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button size="small" @click="pingServer(row)" :loading="pinging[row.id]">检测</el-button>
              <el-button size="small" type="warning" @click="initServer(row)">初始化</el-button>
              <el-button size="small" type="success" @click="installExporter(row)">安装监控</el-button>
              <el-button size="small" type="primary" @click="openDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteServer(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editRow ? '编辑服务器' : '添加服务器'" width="520px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="IP地址" prop="ip">
          <el-input v-model="form.ip" :disabled="!!editRow" />
        </el-form-item>
        <el-form-item label="SSH端口">
          <el-input-number v-model="form.port" :min="1" :max="65535" style="width:100%" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="认证方式">
          <el-radio-group v-model="form.auth_type">
            <el-radio value="password">密码</el-radio>
            <el-radio value="key">密钥</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.auth_type === 'password'" label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item v-else label="私钥">
          <el-input v-model="form.private_key" type="textarea" :rows="4" placeholder="粘贴 PEM 格式私钥" />
        </el-form-item>
        <el-form-item label="分组">
          <el-input v-model="form.group" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveServer">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useLangStore } from '@/stores/lang'
import api from '@/api'

const lang = useLangStore()
const servers = ref([])
const loading = ref(false)
const search = ref('')
const dialogVisible = ref(false)
const editRow = ref(null)
const saving = ref(false)
const pinging = reactive({})
const formRef = ref()

const defaultForm = () => ({
  name: '', ip: '', port: 22, username: 'root',
  auth_type: 'password', password: '', private_key: '', group: 'default', remark: '',
})
const form = reactive(defaultForm())
const rules = {
  name: [{ required: true, message: '请输入名称' }],
  ip: [{ required: true, message: '请输入IP' }],
}

const filtered = computed(() =>
  servers.value.filter(s =>
    !search.value || s.name.includes(search.value) || s.ip.includes(search.value)
  )
)

async function load() {
  loading.value = true
  try {
    const res = await api.get('/servers')
    servers.value = res.data
  } finally {
    loading.value = false
  }
}

function openDialog(row = null) {
  editRow.value = row
  Object.assign(form, row ? { ...row } : defaultForm())
  dialogVisible.value = true
}

async function saveServer() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (editRow.value) {
      await api.put(`/servers/${editRow.value.id}`, form)
      ElMessage.success('更新成功')
    } else {
      await api.post('/servers', form)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function pingServer(row) {
  pinging[row.id] = true
  try {
    await api.post(`/servers/${row.id}/ping`)
    ElMessage.info('检测任务已提交，请稍后刷新')
    setTimeout(load, 3000)
  } finally {
    pinging[row.id] = false
  }
}

async function initServer(row) {
  await ElMessageBox.confirm(`确认初始化服务器 ${row.name}（${row.ip}）？将安装 Docker 等基础环境`, '确认', { type: 'warning' })
  const res = await api.post(`/servers/${row.id}/init`)
  ElMessage.success(`初始化任务已提交，任务ID: ${res.data.task_id}`)
}

async function installExporter(row) {
  await ElMessageBox.confirm(
    `将在 ${row.name}（${row.ip}）安装 node_exporter 并加入 Prometheus 监控，确认？`,
    '安装监控', { type: 'info' }
  )
  const res = await api.post(`/servers/${row.id}/install-exporter`)
  ElMessage.success(`安装任务已提交，任务ID: ${res.data.task_id}，可在 Ansible 任务页查看进度`)
}

async function deleteServer(row) {
  await ElMessageBox.confirm(`确认删除服务器 ${row.name}？`, '确认', { type: 'warning' })
  await api.delete(`/servers/${row.id}`)
  ElMessage.success('删除成功')
  load()
}

onMounted(load)
</script>

<style scoped>
.page-wrap {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  gap: 12px;
}
.toolbar { display: flex; align-items: center; flex-shrink: 0; }
.table-wrap {
  flex: 1;
  overflow: hidden;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
}
.action-btns {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
