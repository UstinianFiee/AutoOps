<template>
  <div class="page-wrap">
    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="openDialog()">
        {{ lang.isZh ? '新建应用' : 'New App' }}
      </el-button>
    </div>

    <div class="app-grid">
      <el-card v-for="app in apps" :key="app.id" class="app-card" shadow="never">
        <div class="app-header">
          <div class="app-title">
            <span class="app-name">{{ app.name }}</span>
            <el-tag size="small" :type="sourceTagType(app.source_type)">
              {{ app.source_type === 'git' ? 'Git' : lang.isZh ? '本地上传' : 'Upload' }}
            </el-tag>
          </div>
          <el-tag :type="statusType(app.status)" size="small">{{ lang.t(app.status) }}</el-tag>
        </div>

        <div class="app-info">
          <div v-if="app.source_type === 'git'">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:4px">
              <circle cx="18" cy="18" r="3" stroke="currentColor" stroke-width="1.8"/>
              <circle cx="6" cy="6" r="3" stroke="currentColor" stroke-width="1.8"/>
              <circle cx="6" cy="18" r="3" stroke="currentColor" stroke-width="1.8"/>
              <path d="M6 9v6M9 6h4a5 5 0 0 1 5 5v4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
            <span class="info-text" :title="app.git_url">{{ app.git_url || '未设置' }}</span>
            <el-tag v-if="app.has_token" size="small" type="success" style="margin-left:4px">Token</el-tag>
          </div>
          <div v-else>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:4px">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="info-text">{{ lang.isZh ? '本地压缩包' : 'Local archive' }}</span>
          </div>
          <div>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:4px">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" stroke="currentColor" stroke-width="1.8"/>
            </svg>
            <span class="info-text">{{ app.deploy_path }}/{{ app.name }}</span>
          </div>
        </div>

        <div class="app-actions">
          <el-button size="small" type="primary" @click="openDialog(app)">
            {{ lang.isZh ? '编辑' : 'Edit' }}
          </el-button>
          <el-button v-if="app.source_type === 'upload'" size="small" type="success" @click="openUpload(app)">
            {{ lang.isZh ? '上传代码' : 'Upload' }}
          </el-button>
          <el-button size="small" @click="showWebhook(app)">Webhook</el-button>
          <el-button size="small" type="danger" @click="deleteApp(app)">
            {{ lang.isZh ? '删除' : 'Delete' }}
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editRow ? (lang.isZh ? '编辑应用' : 'Edit App') : (lang.isZh ? '新建应用' : 'New App')" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-position="top">
        <el-form-item :label="lang.isZh ? '应用名称' : 'App Name'" prop="name">
          <el-input v-model="form.name" :disabled="!!editRow" />
        </el-form-item>

        <el-form-item :label="lang.isZh ? '代码来源' : 'Source Type'">
          <el-radio-group v-model="form.source_type" :disabled="!!editRow">
            <el-radio-button value="git">Git 仓库</el-radio-button>
            <el-radio-button value="upload">{{ lang.isZh ? '本地上传' : 'Local Upload' }}</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="form.source_type === 'git'">
          <el-form-item :label="lang.isZh ? '仓库地址' : 'Repository URL'" prop="git_url">
            <el-input v-model="form.git_url" placeholder="https://github.com/user/repo.git" />
          </el-form-item>
          <el-form-item :label="lang.isZh ? '分支' : 'Branch'">
            <el-input v-model="form.branch" placeholder="main" />
          </el-form-item>
          <el-form-item>
            <template #label>
              <span>{{ lang.isZh ? '访问 Token（私有仓库）' : 'Access Token (private repo)' }}</span>
              <el-tag v-if="editRow?.has_token" size="small" type="success" style="margin-left:6px">{{ lang.isZh ? '已配置' : 'Configured' }}</el-tag>
            </template>
            <el-input
              v-model="form.git_token"
              type="password"
              show-password
              :placeholder="editRow?.has_token ? (lang.isZh ? '留空保持不变' : 'Leave empty to keep') : (lang.isZh ? 'GitHub: ghp_xxx  Gitee: 个人令牌' : 'GitHub: ghp_xxx  Gitee: personal token')"
            />
          </el-form-item>
        </template>

        <el-form-item :label="lang.isZh ? '部署路径' : 'Deploy Path'" prop="deploy_path">
          <el-input v-model="form.deploy_path" placeholder="/opt/apps" />
          <div style="font-size:12px;color:#94a3b8;margin-top:4px">
            {{ lang.isZh ? '代码将部署到：' : 'Code will be deployed to: ' }}{{ form.deploy_path }}/{{ form.name || 'app_name' }}
          </div>
        </el-form-item>

        <el-form-item :label="lang.isZh ? 'docker-compose.yml 内容' : 'docker-compose.yml'">
          <el-input
            v-model="form.compose_content"
            type="textarea"
            :rows="8"
            :placeholder="lang.isZh ? '粘贴 docker-compose.yml 内容（可选，若仓库已有则留空）' : 'Paste docker-compose.yml content (optional)'"
            style="font-family:monospace;font-size:12px"
          />
        </el-form-item>

        <el-form-item :label="lang.isZh ? '备注' : 'Remark'">
          <el-input v-model="form.remark" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ lang.isZh ? '取消' : 'Cancel' }}</el-button>
        <el-button type="primary" :loading="saving" @click="saveApp">{{ lang.isZh ? '保存' : 'Save' }}</el-button>
      </template>
    </el-dialog>

    <!-- 上传代码对话框 -->
    <el-dialog v-model="uploadVisible" :title="lang.isZh ? '上传代码包' : 'Upload Code'" width="520px">
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :limit="1"
        accept=".zip,.tar.gz,.tgz,.tar.bz2"
        :on-change="onFileChange"
        :on-exceed="() => ElMessage.warning(lang.isZh ? '只能上传一个文件' : 'Only one file allowed')"
        :on-remove="() => { uploadFile = null; uploadPreview = null }"
      >
        <el-icon style="font-size:48px;color:#94a3b8"><Upload /></el-icon>
        <div style="margin-top:8px;font-size:14px;color:#374151">
          {{ lang.isZh ? '拖拽文件到此处，或点击选择' : 'Drag file here or click to select' }}
        </div>
        <div style="font-size:12px;color:#94a3b8;margin-top:4px">
          {{ lang.isZh ? '支持 .zip .tar.gz .tgz .tar.bz2，最大 200MB' : 'Supports .zip .tar.gz .tgz .tar.bz2, max 200MB' }}
        </div>
      </el-upload>

      <!-- 文件信息预览 -->
      <div v-if="uploadFile" class="upload-preview">
        <div class="upload-file-info">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" stroke="#3b82f6" stroke-width="1.8"/>
            <polyline points="13 2 13 9 20 9" stroke="#3b82f6" stroke-width="1.8"/>
          </svg>
          <span class="file-name">{{ uploadFile.name }}</span>
          <span class="file-size">{{ (uploadFile.size / 1024 / 1024).toFixed(2) }} MB</span>
        </div>
        <div v-if="uploadFile.size > 200 * 1024 * 1024" class="upload-warn">
          ⚠️ {{ lang.isZh ? '文件超过 200MB 限制' : 'File exceeds 200MB limit' }}
        </div>
        <div v-else class="upload-ok">
          ✓ {{ lang.isZh ? '文件格式和大小校验通过，点击上传即可部署' : 'File validated, click Upload to proceed' }}
        </div>
      </div>

      <!-- 上传进度 -->
      <el-progress v-if="uploadProgress > 0 && uploadProgress < 100" :percentage="uploadProgress" style="margin-top:12px" />

      <template #footer>
        <el-button @click="uploadVisible = false">{{ lang.isZh ? '取消' : 'Cancel' }}</el-button>
        <el-button
          type="primary"
          :loading="uploading"
          @click="doUpload"
          :disabled="!uploadFile || uploadFile.size > 200 * 1024 * 1024"
        >
          {{ lang.isZh ? '上传并保存' : 'Upload & Save' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Webhook 信息对话框 -->
    <el-dialog v-model="webhookVisible" title="Webhook 配置" width="560px">
      <div v-if="webhookInfo">
        <el-alert type="info" :closable="false" style="margin-bottom:16px">
          <template #default>
            {{ lang.isZh ? '在 GitHub/Gitee 仓库设置 → Webhooks 中添加以下地址，当有代码推送时自动触发部署' : 'Add the following URL in GitHub/Gitee repository Settings → Webhooks to auto-deploy on push' }}
          </template>
        </el-alert>
        <el-form label-width="100px" size="small">
          <el-form-item label="Webhook URL">
            <el-input :value="webhookInfo.webhook_url" readonly>
              <template #append>
                <el-button @click="copy(webhookInfo.webhook_url)">{{ lang.isZh ? '复制' : 'Copy' }}</el-button>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item label="Secret">
            <el-input :value="webhookInfo.secret" readonly>
              <template #append>
                <el-button @click="copy(webhookInfo.secret)">{{ lang.isZh ? '复制' : 'Copy' }}</el-button>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item label="Content Type">
            <el-input value="application/json" readonly />
          </el-form-item>
          <el-form-item label="Events">
            <el-tag>push</el-tag>
          </el-form-item>
        </el-form>
        <el-button size="small" type="warning" @click="regenerateWebhook" style="margin-top:8px">
          {{ lang.isZh ? '重新生成 Secret' : 'Regenerate Secret' }}
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus, Upload } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useLangStore } from '@/stores/lang'
import api from '@/api'

const lang = useLangStore()
const apps = ref([])
const dialogVisible = ref(false)
const uploadVisible = ref(false)
const webhookVisible = ref(false)
const editRow = ref(null)
const uploadTarget = ref(null)
const saving = ref(false)
const uploading = ref(false)
const uploadFile = ref(null)
const uploadProgress = ref(0)
const uploadPreview = ref(null)
const webhookInfo = ref(null)
const formRef = ref()
const uploadRef = ref()

const defaultForm = () => ({
  name: '', source_type: 'git', git_url: '', branch: 'main',
  git_token: '', compose_content: '', deploy_path: '/opt/apps', remark: '',
})
const form = reactive(defaultForm())
const rules = {
  name: [{ required: true, message: lang.isZh ? '请输入应用名称' : 'Required' }],
  git_url: [{
    validator: (rule, value, cb) => {
      if (form.source_type === 'git' && !value) cb(new Error(lang.isZh ? '请输入仓库地址' : 'Required'))
      else cb()
    }, trigger: 'blur'
  }],
  deploy_path: [{ required: true, message: lang.isZh ? '请输入部署路径' : 'Required' }],
}

function statusType(s) {
  return { running: 'success', stopped: 'info', deploying: 'warning' }[s] || 'info'
}
function sourceTagType(t) {
  return t === 'git' ? 'primary' : 'warning'
}

async function load() {
  const res = await api.get('/apps')
  apps.value = res.data
}

function openDialog(row = null) {
  editRow.value = row
  Object.assign(form, row ? { ...row, git_token: '' } : defaultForm())
  dialogVisible.value = true
}

async function saveApp() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = { ...form }
    if (!payload.git_token) delete payload.git_token
    if (editRow.value) {
      await api.put(`/apps/${editRow.value.id}`, payload)
      ElMessage.success(lang.isZh ? '更新成功' : 'Updated')
    } else {
      await api.post('/apps', payload)
      ElMessage.success(lang.isZh ? '创建成功' : 'Created')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

function openUpload(app) {
  uploadTarget.value = app
  uploadFile.value = null
  uploadProgress.value = 0
  uploadPreview.value = null
  uploadVisible.value = true
}

function onFileChange(file) {
  uploadFile.value = file.raw
  uploadProgress.value = 0
}

async function doUpload() {
  if (!uploadFile.value || !uploadTarget.value) return
  if (uploadFile.value.size > 200 * 1024 * 1024) {
    return ElMessage.error(lang.isZh ? '文件超过 200MB 限制' : 'File exceeds 200MB limit')
  }
  uploading.value = true
  uploadProgress.value = 0
  try {
    const fd = new FormData()
    fd.append('file', uploadFile.value)
    await api.post(`/apps/${uploadTarget.value.id}/upload`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        uploadProgress.value = Math.round((e.loaded / e.total) * 100)
      },
    })
    ElMessage.success(lang.isZh ? '上传成功，可在 CI/CD 页面触发部署' : 'Uploaded successfully, deploy from CI/CD page')
    uploadVisible.value = false
    load()
  } finally {
    uploading.value = false
  }
}

async function showWebhook(app) {
  const res = await api.get(`/apps/${app.id}/webhook-info`)
  webhookInfo.value = res.data
  webhookInfo.value._app_id = app.id
  webhookVisible.value = true
}

async function regenerateWebhook() {
  if (!webhookInfo.value?._app_id) return
  await ElMessageBox.confirm(lang.isZh ? '重新生成后旧的 Webhook 地址将失效，确认？' : 'Old webhook URL will be invalidated. Confirm?', lang.isZh ? '确认' : 'Confirm', { type: 'warning' })
  const res = await api.post(`/apps/${webhookInfo.value._app_id}/regenerate-webhook`)
  ElMessage.success(lang.isZh ? 'Secret 已重新生成' : 'Secret regenerated')
  showWebhook({ id: webhookInfo.value._app_id })
}

function copy(text) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success(lang.isZh ? '已复制' : 'Copied')
  })
}

async function deleteApp(app) {
  await ElMessageBox.confirm(
    lang.isZh ? `确认删除应用 ${app.name}？相关部署记录也将一并删除` : `Delete app ${app.name}? All deploy records will also be deleted.`,
    lang.isZh ? '确认' : 'Confirm', { type: 'warning' }
  )
  await api.delete(`/apps/${app.id}`)
  ElMessage.success(lang.isZh ? '删除成功' : 'Deleted')
  load()
}

onMounted(load)
</script>

<style scoped>
.page-wrap { display: flex; flex-direction: column; gap: 12px; }
.toolbar { display: flex; }
.app-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.app-card { border-radius: 12px; }
.app-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.app-title { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.app-name { font-size: 15px; font-weight: 600; color: #0f172a; }
.app-info { font-size: 13px; color: #64748b; display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.app-info > div { display: flex; align-items: center; }
.info-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 260px; }
.app-actions { display: flex; gap: 6px; flex-wrap: wrap; }

/* 上传预览 */
.upload-preview {
  margin-top: 12px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}
.upload-file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.file-name { font-weight: 500; color: #374151; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { color: #94a3b8; font-size: 12px; white-space: nowrap; }
.upload-ok { margin-top: 6px; font-size: 12px; color: #16a34a; }
.upload-warn { margin-top: 6px; font-size: 12px; color: #dc2626; }
</style>
