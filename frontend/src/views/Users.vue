<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="openDialog()">新建用户</el-button>
    </div>

    <el-card shadow="never" style="margin-top: 12px">
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="roleType(row.role)" size="small">{{ row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteUser(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editRow ? '编辑用户' : '新建用户'" width="480px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="!!editRow" />
        </el-form-item>
        <el-form-item :label="editRow ? '新密码' : '密码'" :prop="editRow ? '' : 'password'">
          <el-input v-model="form.password" type="password" show-password :placeholder="editRow ? '留空不修改' : ''" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="操作员" value="operator" />
            <el-option label="只读" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item v-if="editRow" label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
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
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const lang = useLangStore()
const users = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editRow = ref(null)
const saving = ref(false)
const formRef = ref()

const defaultForm = () => ({ username: '', password: '', role: 'viewer', email: '', is_active: true })
const form = reactive(defaultForm())
const rules = {
  username: [{ required: true, message: '请输入用户名' }],
  password: [{ required: true, message: '请输入密码' }],
}

function roleType(r) {
  return { admin: 'danger', operator: 'warning', viewer: 'info' }[r] || 'info'
}

function fmt(t) {
  return t ? dayjs.tz(t).format('YYYY-MM-DD HH:mm') : '-'
}

async function load() {
  loading.value = true
  try {
    const res = await api.get('/users')
    users.value = res.data
  } finally {
    loading.value = false
  }
}

function openDialog(row = null) {
  editRow.value = row
  Object.assign(form, row ? { ...row, password: '' } : defaultForm())
  dialogVisible.value = true
}

async function saveUser() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = { ...form }
    if (!payload.password) delete payload.password
    if (editRow.value) {
      await api.put(`/users/${editRow.value.id}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/users', payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function deleteUser(row) {
  if (row.username === auth.username) return ElMessage.warning('不能删除自己')
  await ElMessageBox.confirm(`确认删除用户 ${row.username}？`, '确认', { type: 'warning' })
  await api.delete(`/users/${row.id}`)
  ElMessage.success('删除成功')
  load()
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; }
</style>
