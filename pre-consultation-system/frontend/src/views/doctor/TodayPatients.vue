<template>
  <div class="doctor-page">
    <div class="nav-bar">
      <span class="welcome">医生工作台</span>
      <div class="nav-right">
        <el-button text @click="$router.push({ name: 'FeedbackHistory' })">反馈记录</el-button>
        <el-button text @click="$router.push({ name: 'Profile' })">个人中心</el-button>
        <el-button text type="danger" @click="handleLogout">退出</el-button>
      </div>
    </div>
    <div class="toolbar">
      <el-select v-model="periodFilter" placeholder="时段" clearable @change="fetch">
        <el-option label="上午" value="上午" />
        <el-option label="下午" value="下午" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="状态" clearable @change="fetch">
        <el-option label="等待中" value="等待中" />
        <el-option label="已预约" value="已预约" />
        <el-option label="已就诊" value="已就诊" />
      </el-select>
      <el-button @click="fetch">刷新</el-button>
    </div>
    <el-table :data="patients" stripe @row-click="goReport" style="cursor:pointer">
      <el-table-column prop="registration_id" label="登记号" width="80" />
      <el-table-column prop="patient_id" label="患者ID" />
      <el-table-column prop="time_slot" label="时段" width="80" />
      <el-table-column prop="department" label="科室" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !patients.length" description="暂无患者" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'
import api from '../../api'

const router = useRouter()
const user = useUserStore()
const patients = ref([])
const loading = ref(true)
const periodFilter = ref('')
const statusFilter = ref('等待中')

onMounted(fetch)

async function fetch() {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    if (periodFilter.value) params.period = periodFilter.value
    patients.value = await api.get('/doctor/today-patients', { params })
  } finally {
    loading.value = false
  }
}

function goReport(row) {
  router.push({ name: 'PatientReport', params: { id: row.registration_id } })
}

function handleLogout() {
  user.logout()
  router.push({ name: 'Login' })
}

function statusType(s) {
  const map = { '已预约': '', '等待中': 'warning', '已就诊': 'success', '已过号': 'danger', '已取消': 'info' }
  return map[s] || ''
}
</script>

<style scoped>
.doctor-page { max-width: 900px; margin: 10px auto; padding: 0 16px; }
.nav-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.welcome { font-size: 18px; font-weight: bold; }
.nav-right { display: flex; gap: 8px; }
.toolbar { display: flex; gap: 12px; margin-bottom: 12px; }
</style>
