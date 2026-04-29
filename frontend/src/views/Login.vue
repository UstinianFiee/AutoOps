<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="bg-gradient"></div>
      <div class="floating-orb orb1"></div>
      <div class="floating-orb orb2"></div>
      <div class="floating-orb orb3"></div>
      <div class="brand-watermark">
        <img src="/autoops.png" width="300" height="300" style="opacity:0.07;object-fit:contain" alt=""/>
      </div>
      <div class="left-info">
        <div class="left-logo">
          <img src="/autoops.png" width="60" height="60" style="border-radius:12px;object-fit:contain" alt="AutoOps"/>
          <span>AutoOps</span>
        </div>
        <h2>轻量自动化运维平台</h2>
        <p>统一管理 Docker 服务，一键部署，实时监控告警</p>
        <div class="left-features">
          <div class="lf-item" v-for="f in features" :key="f">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" stroke="rgba(255,255,255,0.7)" stroke-width="2" stroke-linecap="round"/>
              <polyline points="22 4 12 14.01 9 11.01" stroke="rgba(255,255,255,0.7)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>{{ f }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="login-panel">
      <div class="panel-inner">
        <!-- 语言切换 -->
        <div class="login-lang-switch" @click="lang.toggle()">
          <span :class="{ active: lang.isZh }">中</span>
          <span class="sep">/</span>
          <span :class="{ active: !lang.isZh }">EN</span>
        </div>

        <div class="panel-logo">
          <img src="/autoops.png" width="44" height="44" style="border-radius:10px;object-fit:contain" alt="AutoOps"/>
          <span class="panel-logo-text">AutoOps</span>
        </div>

        <h1 class="panel-title">{{ lang.isZh ? '欢迎回来' : 'Welcome Back' }}</h1>
        <p class="panel-sub">{{ lang.isZh ? '登录您的运维平台账号' : 'Sign in to your account' }}</p>

        <transition name="err-slide">
          <div v-if="errorMsg" class="err-bar">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="#ef4444" stroke-width="2"/>
              <line x1="12" y1="8" x2="12" y2="12" stroke="#ef4444" stroke-width="2" stroke-linecap="round"/>
              <circle cx="12" cy="16" r="1" fill="#ef4444"/>
            </svg>
            {{ errorMsg }}
          </div>
        </transition>

        <el-form :model="form" :rules="rules" ref="formRef">
          <div class="field">
            <label>{{ lang.isZh ? '用户名' : 'Username' }}</label>
            <div class="field-box" :class="{ focus: focusField === 0 }">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round"/>
                <circle cx="12" cy="7" r="4" stroke="#94a3b8" stroke-width="1.8"/>
              </svg>
              <el-form-item prop="username" style="flex:1;margin:0">
                <input v-model="form.username" class="field-input" :placeholder="lang.isZh ? '请输入用户名' : 'Enter username'"
                  autocomplete="username"
                  @focus="focusField=0" @blur="focusField=-1" @keyup.enter="handleLogin"/>
              </el-form-item>
            </div>
          </div>

          <div class="field">
            <label>{{ lang.isZh ? '密码' : 'Password' }}</label>
            <div class="field-box" :class="{ focus: focusField === 1 }">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="11" width="18" height="11" rx="2" stroke="#94a3b8" stroke-width="1.8"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round"/>
              </svg>
              <el-form-item prop="password" style="flex:1;margin:0">
                <input v-model="form.password" :type="showPwd ? 'text' : 'password'"
                  class="field-input" :placeholder="lang.isZh ? '请输入密码' : 'Enter password'"
                  autocomplete="current-password"
                  @focus="focusField=1" @blur="focusField=-1" @keyup.enter="handleLogin"/>
              </el-form-item>
              <button type="button" class="eye-btn" @click="showPwd=!showPwd" tabindex="-1">
                <svg v-if="!showPwd" width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="#94a3b8" stroke-width="1.8"/>
                  <circle cx="12" cy="12" r="3" stroke="#94a3b8" stroke-width="1.8"/>
                </svg>
                <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round"/>
                  <line x1="1" y1="1" x2="23" y2="23" stroke="#94a3b8" stroke-width="1.8" stroke-linecap="round"/>
                </svg>
              </button>
            </div>
          </div>

          <button class="login-btn" :class="{loading}" :disabled="loading" @click.prevent="handleLogin">
            <svg v-if="!loading" width="17" height="17" viewBox="0 0 24 24" fill="none">
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3"
                stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else class="spin" width="17" height="17" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="rgba(255,255,255,0.3)" stroke-width="3"/>
              <path d="M12 2a10 10 0 0 1 10 10" stroke="white" stroke-width="3" stroke-linecap="round"/>
            </svg>
            <span>{{ loading ? (lang.isZh ? '登录中...' : 'Signing in...') : (lang.isZh ? '登 录' : 'Sign In') }}</span>
          </button>
        </el-form>

        <p class="panel-footer">AutoOps &copy; 2026 &nbsp;·&nbsp; {{ lang.isZh ? '轻量自动化运维平台' : 'Lightweight DevOps Platform' }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useLangStore } from '@/stores/lang'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const lang = useLangStore()
const auth = useAuthStore()
const formRef = ref()
const loading = ref(false)
const showPwd = ref(false)
const errorMsg = ref('')
const focusField = ref(-1)

const features = ['容器管理 · 一键启停', 'CI/CD 自动化部署', '实时监控 · 多级告警', '日志聚合 · 关键词检索']

const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  errorMsg.value = ''
  try { await formRef.value.validate() } catch { return }
  loading.value = true
  try {
    await auth.login(form)
    router.push('/')
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || (lang.isZh ? '用户名或密码错误' : 'Invalid username or password')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { display:flex; height:100vh; overflow:hidden; }

/* 左侧背景 */
.login-bg {
  flex:1;
  background: linear-gradient(145deg, #0f172a 0%, #1e3a8a 45%, #2563eb 100%);
  position:relative; overflow:hidden;
  display:flex; align-items:center; justify-content:center;
}
.bg-gradient {
  position:absolute; inset:0;
  background: radial-gradient(ellipse at 20% 50%, rgba(99,102,241,0.25) 0%, transparent 55%),
              radial-gradient(ellipse at 80% 10%, rgba(59,130,246,0.2) 0%, transparent 50%);
}
.floating-orb { position:absolute; border-radius:50%; filter:blur(70px); pointer-events:none; }
.orb1 { width:450px;height:450px; background:rgba(59,130,246,0.2); top:-120px;left:-120px; animation:drift1 9s ease-in-out infinite; }
.orb2 { width:320px;height:320px; background:rgba(139,92,246,0.18); bottom:-80px;right:5%; animation:drift2 11s ease-in-out infinite; }
.orb3 { width:220px;height:220px; background:rgba(16,185,129,0.12); top:45%;left:35%; animation:drift3 13s ease-in-out infinite; }
@keyframes drift1 { 0%,100%{transform:translate(0,0)} 50%{transform:translate(50px,35px)} }
@keyframes drift2 { 0%,100%{transform:translate(0,0)} 50%{transform:translate(-35px,-25px)} }
@keyframes drift3 { 0%,100%{transform:translate(0,0)} 50%{transform:translate(25px,-35px)} }
.brand-watermark { position:absolute; bottom:-60px; right:-60px; pointer-events:none; }

/* 左侧文字 */
.left-info { position:relative; z-index:2; padding:48px; color:white; max-width:480px; }
.left-logo { display:flex; align-items:center; gap:12px; margin-bottom:40px; }
.left-logo span { font-size:26px; font-weight:800; letter-spacing:2px; }
.left-info h2 { font-size:30px; font-weight:700; margin:0 0 14px; line-height:1.3; }
.left-info p { font-size:15px; color:rgba(255,255,255,0.65); margin:0 0 36px; line-height:1.7; }
.left-features { display:flex; flex-direction:column; gap:14px; }
.lf-item { display:flex; align-items:center; gap:10px; font-size:14px; color:rgba(255,255,255,0.8); }

/* 右侧面板 */
.login-panel {
  width:460px; min-width:460px;
  background:#fff;
  display:flex; align-items:center; justify-content:center;
  box-shadow:-24px 0 80px rgba(0,0,0,0.18);
}
.panel-inner { width:360px; position:relative; }

.panel-logo { display:flex; align-items:center; gap:10px; margin-bottom:28px; }
.panel-logo-text { font-size:20px; font-weight:800; color:#1e40af; letter-spacing:1px; }
.panel-title { font-size:24px; font-weight:700; color:#0f172a; margin:0 0 6px; }
.panel-sub { font-size:14px; color:#64748b; margin:0 0 24px; }

.err-bar {
  display:flex; align-items:center; gap:8px;
  background:#fef2f2; border:1px solid #fecaca;
  border-radius:8px; padding:10px 14px;
  margin-bottom:16px; color:#ef4444; font-size:13px;
}

.field { margin-bottom:16px; }
.field label { display:block; font-size:13px; font-weight:600; color:#374151; margin-bottom:7px; }
.field-box {
  display:flex; align-items:center; gap:8px;
  background:#f8fafc; border:1.5px solid #e2e8f0;
  border-radius:10px; padding:0 12px;
  transition:border-color .2s, box-shadow .2s;
}
.field-box.focus { border-color:#3b82f6; box-shadow:0 0 0 3px rgba(59,130,246,.12); background:#fff; }
.field-input { flex:1; height:46px; border:none; outline:none; background:transparent; font-size:14px; color:#0f172a; padding:0; }
.field-input::placeholder { color:#cbd5e1; }
.eye-btn { background:none; border:none; padding:0; cursor:pointer; display:flex; align-items:center; }

.login-btn {
  width:100%; height:48px; margin-top:8px;
  border:none; border-radius:10px;
  background:linear-gradient(135deg,#3b82f6,#0284c7);
  color:white; font-size:15px; font-weight:600; letter-spacing:3px;
  cursor:pointer; display:flex; align-items:center; justify-content:center; gap:8px;
  transition:opacity .2s,transform .15s,box-shadow .2s;
  box-shadow:0 4px 16px rgba(59,130,246,.4);
}
.login-btn:hover:not(:disabled) { opacity:.9; transform:translateY(-1px); box-shadow:0 8px 24px rgba(59,130,246,.45); }
.login-btn:active:not(:disabled) { transform:translateY(0); }
.login-btn:disabled { opacity:.7; cursor:not-allowed; }
.spin { animation:spin .8s linear infinite; }
@keyframes spin { to{transform:rotate(360deg)} }

.panel-footer { text-align:center; font-size:12px; color:#94a3b8; margin-top:28px; }

.err-slide-enter-active { animation:errIn .3s ease; }
@keyframes errIn { from{opacity:0;transform:translateY(-6px)} to{opacity:1;transform:translateY(0)} }

.login-lang-switch {
  position: absolute;
  top: 20px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 3px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  user-select: none;
  padding: 4px 8px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  transition: all 0.15s;
}
.login-lang-switch:hover { border-color: #93c5fd; background: #eff6ff; }
.login-lang-switch .active { color: #2563eb; }
.login-lang-switch .sep { color: #cbd5e1; }
:deep(.el-form-item) { margin-bottom:0; }
:deep(.el-form-item__error) { padding-top:4px; font-size:12px; color:#ef4444; }
</style>
