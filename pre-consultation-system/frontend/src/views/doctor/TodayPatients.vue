<template>
  <div class="doctor-page">
    <el-container>
      <el-header>
        <div class="header-bar">
          <span>医生接诊工作台</span>
          <el-button text @click="logout">退出登录</el-button>
        </div>
      </el-header>
      <el-main>
        <el-card>
          <template #header>
            <div class="filter-bar">
              <span>今日患者</span>
              <div>
                <el-select v-model="timeSlot" placeholder="时段" clearable style="width:120px;margin-right:8px">
                  <el-option label="上午" value="上午" />
                  <el-option label="下午" value="下午" />
                  <el-option label="晚上" value="晚上" />
                </el-select>
                <el-button @click="load">刷新</el-button>
              </div>
            </div>
          </template>
          <el-table :data="patients" v-loading="loading" stripe @row-click="goReport">
            <el-table-column prop="registration_id" label="登记号" width="100" />
            <el-table-column prop="patient_id" label="患者" />
            <el-table-column prop="time_slot" label="时段" width="80" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === '等待中' ? 'warning' : row.status === '已就诊' ? 'success' : ''">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'
import api from '../../api'

const router = useRouter()
const store = useUserStore()
const patients = ref([])
const loading = ref(false)
const timeSlot = ref('')

async function load() {
  loading.value = true
  try {
    const params = { status: '等待中' }
    if (timeSlot.value) params.time_slot = timeSlot.value
    patients.value = await api.get('/doctor/today-patients', { params })
  } finally {
    loading.value = false
  }
}

function goReport(row) {
  router.push(`/doctor/patient/${row.registration_id}`)
}

function logout() {
  store.logout()
  router.push('/login')
}

watch(timeSlot, load)
load()
</script>

<style scoped>
.doctor-page { max-width: 900px; margin: 0 auto; }
.header-bar { display: flex; justify-content: space-between; align-items: center; }
.filter-bar { display: flex; justify-content: space-between; align-items: center; }
</style>
