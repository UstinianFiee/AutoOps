<template>
  <div class="terminal-page">
    <!-- 顶部工具栏 -->
    <div class="terminal-toolbar">
      <div class="toolbar-left">
        <!-- 模式切换 -->
        <el-radio-group v-model="connMode" size="small" style="margin-right:10px" @change="onModeChange">
          <el-radio-button value="saved">已保存服务器</el-radio-button>
          <el-radio-button value="custom">自定义连接</el-radio-button>
        </el-radio-group>

        <!-- 已保存服务器模式 -->
        <template v-if="connMode === 'saved'">
          <el-select v-model="selectedServerId" placeholder="选择服务器" size="small"
            style="width:220px" @change="onServerChange">
            <el-option v-for="s in servers" :key="s.id" :value="s.id"
              :label="`${s.name} (${s.ip})`">
              <span :style="{ color: s.status === 'online' ? '#16a34a' : '#94a3b8' }">●</span>
              &nbsp;{{ s.name }}
              <span style="float:right;color:#94a3b8;font-size:12px">{{ s.ip }}</span>
            </el-option>
          </el-select>
        </template>

        <!-- 自定义连接模式 -->
        <template v-else>
          <el-input v-model="custom.host" placeholder="IP 或主机名" size="small" style="width:150px" />
          <el-input v-model.number="custom.port" placeholder="端口" size="small" style="width:70px;margin-left:4px" />
          <el-input v-model="custom.username" placeholder="用户名" size="small" style="width:100px;margin-left:4px" />
          <el-select v-model="custom.auth_type" size="small" style="width:80px;margin-left:4px">
            <el-option value="password" label="密码" />
            <el-option value="key" label="密钥" />
          </el-select>
          <el-input v-if="custom.auth_type === 'password'" v-model="custom.password"
            placeholder="密码" type="password" show-password size="small" style="width:130px;margin-left:4px" />
          <el-button v-else size="small" style="margin-left:4px" @click="showKeyDialog = true">
            {{ custom.private_key ? '已填写密钥 ✓' : '填写私钥' }}
          </el-button>
        </template>

        <el-button type="primary" size="small" style="margin-left:8px"
          :loading="connecting" :disabled="!canConnect || connected" @click="connect">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:4px">
            <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          连接
        </el-button>
        <el-button size="small" style="margin-left:4px" :disabled="!connected" @click="disconnect">断开</el-button>
        <el-button size="small" style="margin-left:4px" :disabled="!connected" @click="clearTerminal">清屏</el-button>

        <el-divider direction="vertical" style="margin:0 8px" />

        <el-button size="small" :type="showFiles ? 'primary' : ''" :disabled="!connected"
          @click="toggleFilePanel">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:4px">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
              stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
          </svg>
          文件管理
        </el-button>
      </div>

      <div class="toolbar-right">
        <div class="conn-status" :class="connected ? 'online' : 'offline'">
          <span class="status-dot"></span>
          {{ connected ? `已连接 · ${connLabel}` : '未连接' }}
        </div>
      </div>
    </div>

    <!-- 主体：终端 + 文件面板 -->
    <div class="body-wrap">
      <!-- 文件管理侧边栏 -->
      <transition name="slide-panel">
        <div v-if="showFiles && connected" class="file-panel">
          <!-- 路径导航 -->
          <div class="fp-header">
            <div class="fp-path-bar">
              <el-button size="small" :icon="ArrowLeft" circle :disabled="pathHistory.length <= 1"
                @click="goBack" style="flex-shrink:0" />
              <el-input v-model="currentPath" size="small" style="flex:1"
                @keyup.enter="loadDir(currentPath)" />
              <el-button size="small" :icon="Refresh" circle :loading="loadingFiles"
                @click="loadDir(currentPath)" style="flex-shrink:0" />
            </div>
            <div class="fp-actions">
              <el-button size="small" @click="showMkdirDialog = true">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:3px">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
                    stroke="currentColor" stroke-width="1.8"/>
                  <line x1="12" y1="11" x2="12" y2="17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                  <line x1="9" y1="14" x2="15" y2="14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                </svg>
                新建目录
              </el-button>
              <el-upload :show-file-list="false" :before-upload="handleUpload" :auto-upload="false"
                @change="onFileSelected" style="display:inline-block">
                <el-button size="small" type="primary" :loading="uploading">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:3px">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                    <polyline points="17 8 12 3 7 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                    <line x1="12" y1="3" x2="12" y2="15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                  </svg>
                  上传
                </el-button>
              </el-upload>
            </div>
          </div>

          <!-- 文件列表 -->
          <div class="fp-list" v-loading="loadingFiles">
            <!-- 上级目录 -->
            <div v-if="currentPath !== '/'" class="fp-item fp-item-dir" @dblclick="goUp">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" class="fp-icon dir">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
                  stroke="#f59e0b" stroke-width="1.8" fill="#fef3c7"/>
              </svg>
              <span class="fp-name" style="color:#94a3b8">..</span>
            </div>

            <div
              v-for="entry in fileEntries"
              :key="entry.path"
              class="fp-item"
              :class="{ 'fp-item-dir': entry.is_dir, selected: selectedFile?.path === entry.path }"
              @click="selectedFile = entry"
              @dblclick="entry.is_dir ? loadDir(entry.path) : null"
              @contextmenu.prevent="openContextMenu($event, entry)"
            >
              <!-- 目录图标 -->
              <svg v-if="entry.is_dir" width="14" height="14" viewBox="0 0 24 24" fill="none" class="fp-icon">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
                  stroke="#f59e0b" stroke-width="1.8" fill="#fef3c7"/>
              </svg>
              <!-- 文件图标 -->
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" class="fp-icon">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
                  stroke="#60a5fa" stroke-width="1.8" fill="#eff6ff"/>
                <polyline points="14 2 14 8 20 8" stroke="#60a5fa" stroke-width="1.8"/>
              </svg>

              <span class="fp-name" :title="entry.name">{{ entry.name }}</span>
              <span class="fp-size">{{ entry.size_str }}</span>
            </div>

            <div v-if="!loadingFiles && fileEntries.length === 0" class="fp-empty">
              目录为空
            </div>
          </div>

          <!-- 右键菜单 -->
          <div v-if="ctxMenu.visible" class="ctx-menu"
            :style="{ top: ctxMenu.y + 'px', left: ctxMenu.x + 'px' }"
            @mouseleave="ctxMenu.visible = false">
            <div class="ctx-item" @click="downloadFile(ctxMenu.entry)" v-if="!ctxMenu.entry?.is_dir">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><polyline points="7 10 12 15 17 10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="12" y1="15" x2="12" y2="3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
              下载
            </div>
            <div class="ctx-item" @click="startRename(ctxMenu.entry)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
              重命名
            </div>
            <div class="ctx-item danger" @click="confirmDelete(ctxMenu.entry)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><polyline points="3 6 5 6 21 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M10 11v6M14 11v6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
              删除
            </div>
          </div>
        </div>
      </transition>

      <!-- 终端区域 -->
      <div class="terminal-wrap">
        <div ref="terminalEl" class="terminal-inner" />
        <div v-if="!connected && !connecting" class="terminal-placeholder">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" style="color:#334155;margin-bottom:12px">
            <rect x="2" y="3" width="20" height="14" rx="2" stroke="currentColor" stroke-width="1.5"/>
            <path d="M8 21h8M12 17v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M7 8l3 3-3 3M13 14h4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <p>选择服务器后点击「连接」打开 SSH 终端</p>
        </div>
      </div>
    </div>

    <!-- 新建目录对话框 -->
    <el-dialog v-model="showMkdirDialog" title="新建目录" width="360px">
      <el-input v-model="mkdirName" placeholder="目录名称" @keyup.enter="mkdir" />
      <template #footer>
        <el-button @click="showMkdirDialog = false">取消</el-button>
        <el-button type="primary" @click="mkdir">创建</el-button>
      </template>
    </el-dialog>

    <!-- 重命名对话框 -->
    <el-dialog v-model="showRenameDialog" title="重命名" width="360px">
      <el-input v-model="renameTo" placeholder="新名称" @keyup.enter="doRename" />
      <template #footer>
        <el-button @click="showRenameDialog = false">取消</el-button>
        <el-button type="primary" @click="doRename">确认</el-button>
      </template>
    </el-dialog>

    <!-- 自定义连接私钥对话框 -->
    <el-dialog v-model="showKeyDialog" title="填写私钥" width="480px">
      <el-input v-model="custom.private_key" type="textarea" :rows="10"
        placeholder="粘贴 PEM 格式私钥，例如：&#10;-----BEGIN RSA PRIVATE KEY-----&#10;...&#10;-----END RSA PRIVATE KEY-----"
        style="font-family:monospace;font-size:12px" />
      <template #footer>
        <el-button @click="showKeyDialog = false">取消</el-button>
        <el-button type="primary" @click="showKeyDialog = false">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const servers = ref([])
const selectedServerId = ref(null)
const connecting = ref(false)
const connected = ref(false)

// 连接模式
const connMode = ref('saved')  // 'saved' | 'custom'
const custom = reactive({
  host: '', port: 22, username: 'root',
  auth_type: 'password', password: '', private_key: '',
})
const showKeyDialog = ref(false)

// 终端
const terminalEl = ref(null)
let term = null
let fitAddon = null
let ws = null
let resizeObserver = null

// 文件管理
const showFiles = ref(false)
const currentPath = ref('/')
const fileEntries = ref([])
const loadingFiles = ref(false)
const selectedFile = ref(null)
const pathHistory = ref(['/'])
const uploading = ref(false)

// 对话框
const showMkdirDialog = ref(false)
const mkdirName = ref('')
const showRenameDialog = ref(false)
const renameTo = ref('')
const renameTarget = ref(null)

// 右键菜单
const ctxMenu = ref({ visible: false, x: 0, y: 0, entry: null })

const currentServer = computed(() =>
  servers.value.find(s => s.id === selectedServerId.value)
)

const canConnect = computed(() => {
  if (connMode.value === 'saved') return !!selectedServerId.value
  return !!(custom.host && custom.port && custom.username &&
    (custom.auth_type === 'password' ? custom.password : custom.private_key))
})

const connLabel = computed(() => {
  if (connMode.value === 'saved') return currentServer.value?.name || ''
  return `${custom.username}@${custom.host}:${custom.port}`
})

// 自定义连接时文件管理用的 server_id（null 表示用自定义参数）
const fileServerId = computed(() =>
  connMode.value === 'saved' ? selectedServerId.value : null
)

// ── 终端 ──────────────────────────────────────────────────────────────────────

function initTerminal() {
  if (term) term.dispose()
  term = new Terminal({
    theme: {
      background: '#0d1117', foreground: '#e6edf3', cursor: '#58a6ff',
      cursorAccent: '#0d1117', selectionBackground: '#264f78',
      black: '#484f58', red: '#ff7b72', green: '#3fb950', yellow: '#d29922',
      blue: '#58a6ff', magenta: '#bc8cff', cyan: '#39c5cf', white: '#b1bac4',
      brightBlack: '#6e7681', brightRed: '#ffa198', brightGreen: '#56d364',
      brightYellow: '#e3b341', brightBlue: '#79c0ff', brightMagenta: '#d2a8ff',
      brightCyan: '#56d4dd', brightWhite: '#f0f6fc',
    },
    fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, 'Courier New', monospace",
    fontSize: 14, lineHeight: 1.4, cursorBlink: true, cursorStyle: 'block',
    scrollback: 5000,
  })
  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(terminalEl.value)
  fitAddon.fit()

  term.onData(data => {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(data)
  })

  resizeObserver = new ResizeObserver(() => {
    if (fitAddon) {
      fitAddon.fit()
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(`__resize__:${term.cols}:${term.rows}`)
      }
    }
  })
  resizeObserver.observe(terminalEl.value)
}

function connect() {
  if (!canConnect.value) return
  connecting.value = true
  nextTick(() => {
    initTerminal()
    const token = auth.token
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'

    let url
    if (connMode.value === 'saved') {
      url = `${proto}//${location.host}/api/terminal/ws?server_id=${selectedServerId.value}&token=${encodeURIComponent(token)}`
    } else {
      // 自定义连接：把参数编码进 URL
      const p = new URLSearchParams({
        host: custom.host,
        port: String(custom.port),
        username: custom.username,
        auth_type: custom.auth_type,
        token,
      })
      if (custom.auth_type === 'password') {
        p.set('password', custom.password)
      } else {
        p.set('private_key', custom.private_key)
      }
      url = `${proto}//${location.host}/api/terminal/ws-custom?${p.toString()}`
    }

    ws = new WebSocket(url)
    ws.binaryType = 'arraybuffer'
    ws.onopen = () => { connecting.value = false; connected.value = true; term.focus() }
    ws.onmessage = (e) => {
      if (e.data instanceof ArrayBuffer) term.write(new Uint8Array(e.data))
      else term.write(e.data)
    }
    ws.onerror = () => {
      connecting.value = false; connected.value = false
      term.write('\r\n\x1b[31m[ERROR] WebSocket 连接失败\x1b[0m\r\n')
    }
    ws.onclose = (e) => {
      connecting.value = false; connected.value = false
      if (term) term.write(`\r\n\x1b[33m[AutoOps] 连接已断开 (code: ${e.code})\x1b[0m\r\n`)
    }
  })
}

function onModeChange() {
  if (connected.value) disconnect()
}

function disconnect() {
  if (ws) { ws.close(); ws = null }
  connected.value = false
  showFiles.value = false
}

function clearTerminal() { if (term) term.clear() }

function onServerChange() { if (connected.value) disconnect() }

// ── 文件管理 ──────────────────────────────────────────────────────────────────

function toggleFilePanel() {
  if (connMode.value === 'custom') {
    ElMessage.warning('自定义连接暂不支持文件管理，请将服务器保存后使用')
    return
  }
  showFiles.value = !showFiles.value
  if (showFiles.value && fileEntries.value.length === 0) {
    loadDir('/')
  }
  nextTick(() => { if (fitAddon) fitAddon.fit() })
}

async function loadDir(path) {
  loadingFiles.value = true
  selectedFile.value = null
  try {
    const res = await api.get('/sftp/list', {
      params: { server_id: selectedServerId.value, path }
    })
    currentPath.value = res.data.path
    fileEntries.value = res.data.entries
    // 记录历史
    if (pathHistory.value[pathHistory.value.length - 1] !== path) {
      pathHistory.value.push(path)
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载目录失败')
  } finally {
    loadingFiles.value = false
  }
}

function goBack() {
  if (pathHistory.value.length <= 1) return
  pathHistory.value.pop()
  const prev = pathHistory.value[pathHistory.value.length - 1]
  loadDir(prev)
}

function goUp() {
  const parts = currentPath.value.replace(/\/$/, '').split('/')
  parts.pop()
  const parent = parts.join('/') || '/'
  loadDir(parent)
}

// 上传
function onFileSelected(file) {
  uploadFile(file.raw)
}

function handleUpload() { return false } // 阻止自动上传

async function uploadFile(file) {
  uploading.value = true
  const formData = new FormData()
  formData.append('file', file)
  try {
    await api.post('/sftp/upload', formData, {
      params: { server_id: selectedServerId.value, path: currentPath.value },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ElMessage.success(`上传成功: ${file.name}`)
    loadDir(currentPath.value)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

// 下载
function downloadFile(entry) {
  ctxMenu.value.visible = false
  const token = auth.token
  const url = `/api/sftp/download?server_id=${selectedServerId.value}&path=${encodeURIComponent(entry.path)}`
  // 用带 Authorization 的 fetch 下载
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then(res => {
      if (!res.ok) throw new Error('下载失败')
      return res.blob()
    })
    .then(blob => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = entry.name
      a.click()
      URL.revokeObjectURL(a.href)
    })
    .catch(e => ElMessage.error(e.message))
}

// 删除
async function confirmDelete(entry) {
  ctxMenu.value.visible = false
  await ElMessageBox.confirm(
    `确认删除 ${entry.is_dir ? '目录' : '文件'} "${entry.name}"？${entry.is_dir ? '目录内所有内容将被删除！' : ''}`,
    '确认删除', { type: 'warning' }
  )
  try {
    await api.delete('/sftp/delete', {
      params: { server_id: selectedServerId.value, path: entry.path }
    })
    ElMessage.success('删除成功')
    loadDir(currentPath.value)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

// 重命名
function startRename(entry) {
  ctxMenu.value.visible = false
  renameTarget.value = entry
  renameTo.value = entry.name
  showRenameDialog.value = true
}

async function doRename() {
  if (!renameTo.value.trim()) return
  const dir = currentPath.value.replace(/\/$/, '')
  const newPath = dir + '/' + renameTo.value.trim()
  try {
    await api.post('/sftp/rename', {
      server_id: selectedServerId.value,
      old_path: renameTarget.value.path,
      new_path: newPath,
    })
    ElMessage.success('重命名成功')
    showRenameDialog.value = false
    loadDir(currentPath.value)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重命名失败')
  }
}

// 新建目录
async function mkdir() {
  if (!mkdirName.value.trim()) return
  const newPath = currentPath.value.replace(/\/$/, '') + '/' + mkdirName.value.trim()
  try {
    await api.post('/sftp/mkdir', {
      server_id: selectedServerId.value,
      path: newPath,
    })
    ElMessage.success('目录创建成功')
    showMkdirDialog.value = false
    mkdirName.value = ''
    loadDir(currentPath.value)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}

// 右键菜单
function openContextMenu(e, entry) {
  selectedFile.value = entry
  const rect = e.currentTarget.closest('.file-panel').getBoundingClientRect()
  ctxMenu.value = {
    visible: true,
    x: e.clientX - rect.left,
    y: e.clientY - rect.top,
    entry,
  }
}

// 点击其他地方关闭右键菜单
function onDocClick() { ctxMenu.value.visible = false }

onMounted(async () => {
  document.addEventListener('click', onDocClick)
  try {
    const res = await api.get('/servers')
    servers.value = res.data
  } catch { servers.value = [] }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  disconnect()
  if (resizeObserver) resizeObserver.disconnect()
  if (term) { term.dispose(); term = null }
})
</script>

<style scoped>
.terminal-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  gap: 10px;
}

.terminal-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 16px;
  flex-shrink: 0;
}
.toolbar-left { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.toolbar-right { display: flex; align-items: center; gap: 12px; }

.conn-status {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 500;
  padding: 4px 10px; border-radius: 20px;
}
.conn-status.online { background: #f0fdf4; color: #16a34a; }
.conn-status.offline { background: #f8fafc; color: #94a3b8; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }

/* ── 主体布局 ── */
.body-wrap {
  flex: 1;
  display: flex;
  gap: 10px;
  overflow: hidden;
  min-height: 0;
}

/* ── 文件面板 ── */
.file-panel {
  width: 280px;
  min-width: 280px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.fp-header {
  padding: 10px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}
.fp-path-bar { display: flex; align-items: center; gap: 4px; }
.fp-actions { display: flex; gap: 4px; }

.fp-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}
.fp-list::-webkit-scrollbar { width: 4px; }
.fp-list::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 2px; }

.fp-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  cursor: pointer;
  font-size: 12.5px;
  color: #374151;
  user-select: none;
  transition: background 0.1s;
}
.fp-item:hover { background: #f8fafc; }
.fp-item.selected { background: #eff6ff; }
.fp-item-dir { color: #1e40af; }
.fp-icon { flex-shrink: 0; }
.fp-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fp-size { font-size: 11px; color: #94a3b8; flex-shrink: 0; }
.fp-empty { text-align: center; color: #94a3b8; font-size: 12px; padding: 24px 0; }

/* 右键菜单 */
.ctx-menu {
  position: absolute;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  z-index: 100;
  min-width: 120px;
  padding: 4px 0;
}
.ctx-item {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  font-size: 13px;
  cursor: pointer;
  color: #374151;
  transition: background 0.1s;
}
.ctx-item:hover { background: #f1f5f9; }
.ctx-item.danger { color: #ef4444; }
.ctx-item.danger:hover { background: #fef2f2; }

/* ── 终端 ── */
.terminal-wrap {
  flex: 1;
  background: #0d1117;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
  border: 1px solid #21262d;
  min-width: 0;
}
.terminal-inner {
  width: 100%; height: 100%;
  padding: 8px; box-sizing: border-box;
}
:deep(.xterm) { height: 100%; }
:deep(.xterm-viewport) { border-radius: 8px; }

.terminal-placeholder {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  color: #4b5563; font-size: 14px;
  pointer-events: none;
}
.terminal-placeholder p { margin: 0; color: #6b7280; }

/* 面板滑入动画 */
.slide-panel-enter-active, .slide-panel-leave-active {
  transition: width 0.2s ease, opacity 0.2s ease, min-width 0.2s ease;
}
.slide-panel-enter-from, .slide-panel-leave-to {
  width: 0 !important;
  min-width: 0 !important;
  opacity: 0;
}
</style>
