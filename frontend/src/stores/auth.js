import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const role = ref(localStorage.getItem('role') || '')

  const isAdmin = computed(() => role.value === 'admin')
  const isOperator = computed(() => ['admin', 'operator'].includes(role.value))

  async function login(credentials) {
    const res = await api.post('/auth/login', credentials)
    token.value = res.data.access_token
    username.value = res.data.username
    role.value = res.data.role
    localStorage.setItem('token', token.value)
    localStorage.setItem('username', username.value)
    localStorage.setItem('role', role.value)
  }

  function logout() {
    token.value = ''
    username.value = ''
    role.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
    router.push('/login')
  }

  return { token, username, role, isAdmin, isOperator, login, logout }
})
