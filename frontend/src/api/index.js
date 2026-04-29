import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 简单内存缓存（GET 请求，5秒内不重复请求）
const _cache = new Map()
const CACHE_TTL = 5000

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
      const isLoginRequest = err.config?.url?.includes('/auth/login')
      if (!isLoginRequest) {
        localStorage.removeItem('token')
        localStorage.removeItem('username')
        localStorage.removeItem('role')
        window.location.href = '/login'
      }
    } else if (status === 409) {
      // 并发冲突（部署锁），直接显示
      ElMessage.warning(msg)
    } else if (status >= 500) {
      ElMessage.error(`服务器错误 (${status}): ${msg}`)
    } else if (status !== 404) {
      ElMessage.error(msg)
    }

    return Promise.reject(err)
  }
)

export default api
