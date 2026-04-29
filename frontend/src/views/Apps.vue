<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="openDialog()">新建应用</el-button>
    </div>

    <el-row :gutter="16" style="margin-top: 12px">
      <el-col :span="8" v-for="app in apps" :key="app.id">
        <el-card class="app-card" shadow="never">
          <div class="app-header">
            <span class="app-name">{{ app.name }}</span>
            <el-tag :type="statusType(app.status)" size="small">{{ app.status }}</el-tag>
          </div>
          <div class="app-info">
            <div><el-icon><Link /></el-icon> {{ app.git_url || '无 Git 地址' }}</div>
            <div><el-icon><Branch /></el-icon> 分支: {{ app.branch }}</div>
            <div><el-icon><Connection /></el-icon> 服务器ID: {{ app.server_id || '未绑定' }}</div>
            <div><el-icon><FolderOpened /></el-icon> {{ app.deploy_path }}</div>
          </div>
          <div class="app-actions">
            <el-button size="small" type="success" @click="startApp(app)" :disabled="app.status === 'running'">启动</el-button>
            <el-button size="small" type="warning" @click="stopApp(app)" :disabled="app.status === 'stopped'">停止</el-button>
            <el-button size="small" type="primary" @click="openDialog(app)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteApp(app)">删除</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 对话框 -->
    <el-dialog v-model="dialogVisible" :title="editRow ? '编辑应用' : '新建应用'" width="640px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-form-item label="应用名称" prop="name">
          <el-input v-model="form.name" :disabled="!!editRow" />
        </el-form-item>
        <el-form-item label="Git 地址">
          <el-input v-model="form.git_url" placeholder="https://gitlab.example.com/group/repo.git" />
        </el-form-item>
        <el-form-item label="分支">
          <el-input v-model="form.branch" />
        </el-form-item>
        <el-form-item label="绑定服务器">
          <el-select v-model="form.server_id" placeholder="选择服务器" clearable style="width: 100%">
            <el-option v-for="s in servers" :key="s.id" :label="`${s.name} (${s.ip})`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="部署路径">
          <el-input v-model="form.deploy_path" />
        </el-form-item>
        <el-form-item label="docker-compose">
          <el-input
            v-model="form.compose_content"
            type="textarea"
            :rows="8"
            placeholder="粘贴 docker-compose.yml 内容（可选）"
            style="font-family: monospace; font-size: 12px"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveApp">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useLangStore } from '@/stores/lang'
import api from '@/api'

const apps = ref([])
const lang = useLangStore()
const servers = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editRow = ref(null)
const saving = ref(false)
const formRef = ref()

const defaultForm = () => ({
  name: '', git_url: '', branch: 'main', server_id: null,
  compose_content: '', deploy_path: '/opt/apps', remark: '',
})
const form = reactive(defaultForm())
const rules = { name: [{ required: true, message: '请输入应用名称' }] }

function statusType(s) {
  return { running: 'success', stopped: 'info', deploying: 'warning' }[s] || 'info'
}

async function load() {
  const [a, s] = await Promise.all([api.get('/apps'), api.get('/servers')])
  apps.value = a.data
  servers.value = s.data
}

function openDialog(row = null) {
  editRow.value = row
  Object.assign(form, row ? { ...row } : defaultForm())
  dialogVisible.value = true
}

async function saveApp() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (editRow.value) {
      await api.put(`/apps/${editRow.value.id}`, form)
      ElMessage.success('更新成功')
    } else {
      await api.post('/apps', form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function startApp(app) {
  await api.post(`/apps/${app.id}/start`)
  ElMessage.success(`${app.name} 已启动`)
  load()
}

async function stopApp(app) {
  await api.post(`/apps/${app.id}/stop`)
  ElMessage.success(`${app.name} 已停止`)
  load()
}

async function deleteApp(app) {
  await ElMessageBox.confirm(`确认删除应用 ${app.name}？`, '确认', { type: 'warning' })
  await api.delete(`/apps/${app.id}`)
  ElMessage.success('删除成功')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; }
.app-card { margin-bottom: 16px; border-radius: 8px; }
.app-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.app-name { font-size: 16px; font-weight: 600; color: #303133; }
.app-info { font-size: 13px; color: #606266; line-height: 2; }
.app-info > div { display: flex; align-items: center; gap: 6px; }
.app-actions { margin-top: 12px; display: flex; gap: 8px; }
</style>
