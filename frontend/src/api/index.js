import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截：注入 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截：统一错误处理
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status
    const msg = err.response?.data?.detail || err.message || '请求失败'

    if (status === 401) {
      // 只有已登录状态下收到 401 才跳转（登录接口本身的 401 由调用方处理）
      const isLoginRequest = err.config?.url?.includes('/auth/login')
      if (!isLoginRequest) {
        localStorage.removeItem('token')
        localStorage.removeItem('username')
        localStorage.removeItem('role')
        window.location.href = '/login'
      }
      // 登录接口的 401 直接抛出，由 Login.vue 的 catch 处理
    } else {
      ElMessage.error(msg)
    }

    return Promise.reject(err)
  }
)

export default api
