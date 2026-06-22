import axios from 'axios'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

api.interceptors.request.use((config) => {
  const store = useUserStore()
  if (store.token) {
    config.headers.Authorization = `Bearer ${store.token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message
    ElMessage.error(msg)
    if (err.response?.status === 401) {
      const store = useUserStore()
      store.logout()
      window.location.hash = '#/login'
    }
    return Promise.reject(err)
  },
)

export default api
