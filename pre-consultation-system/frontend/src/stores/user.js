import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useUserStore = defineStore('user', () => {
  // 使用 sessionStorage 而非 localStorage：
  // 关闭标签页自动清除 token，降低 XSS 窃取风险。
  // 若需要跨标签页保持登录，可改回 localStorage。
  const token = ref(sessionStorage.getItem('token') || '')
  const role = ref(sessionStorage.getItem('role') || '')
  const username = ref(sessionStorage.getItem('username') || '')

  const isLoggedIn = computed(() => !!token.value)
  const isDoctor = computed(() => role.value === 'doctor')
  const isAdmin = computed(() => role.value === 'admin')

  async function login(user, pass) {
    const res = await api.post('/auth/login', { username: user, password: pass })
    token.value = res.access_token
    role.value = res.role
    username.value = user
    sessionStorage.setItem('token', res.access_token)
    sessionStorage.setItem('role', res.role)
    sessionStorage.setItem('username', user)
  }

  function logout() {
    token.value = ''
    role.value = ''
    username.value = ''
    sessionStorage.removeItem('token')
    sessionStorage.removeItem('role')
    sessionStorage.removeItem('username')
  }

  return { token, role, username, isLoggedIn, isDoctor, isAdmin, login, logout }
})
