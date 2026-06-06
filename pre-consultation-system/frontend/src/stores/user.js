import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const role = ref(localStorage.getItem('role') || '')
  const username = ref(localStorage.getItem('username') || '')

  const isLoggedIn = computed(() => !!token.value)
  const isDoctor = computed(() => role.value === 'doctor')
  const isAdmin = computed(() => role.value === 'admin')

  async function login(user, pass) {
    const res = await api.post('/auth/login', { username: user, password: pass })
    token.value = res.access_token
    role.value = res.role
    username.value = user
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('role', res.role)
    localStorage.setItem('username', user)
  }

  function logout() {
    token.value = ''
    role.value = ''
    username.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('role')
    localStorage.removeItem('username')
  }

  return { token, role, username, isLoggedIn, isDoctor, isAdmin, login, logout }
})
