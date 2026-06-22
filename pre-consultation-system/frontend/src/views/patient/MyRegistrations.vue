<template>
  <div class="reg-list-page">
    <div class="nav-bar">
      <el-button text @click="$router.push({ name: 'Consultation' })"><ArrowLeft />返回问诊</el-button>
      <el-button text @click="$router.push({ name: 'RegistrationConfirm' })"><DocumentAdd />直接挂号</el-button>
      <el-button text @click="$router.push({ name: 'Profile' })"><User />个人中心</el-button>
    </div>
    <el-card>
      <template #header><h2><List style="margin-right:6px" />我的挂号记录</h2></template>
      <div v-if="loading" v-loading="true" style="min-height:120px" />
      <el-table v-else-if="list.length" :data="list" stripe>
        <el-table-column prop="registration_date" label="日期" width="120" />
        <el-table-column prop="time_slot" label="时段" width="80" />
        <el-table-column prop="department" label="科室" />
        <el-table-column prop="doctor" label="医生" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无挂号记录" />
      <el-button type="primary" @click="$router.push({ name: 'Consultation' })" style="margin-top:16px;width:100%"><Refresh style="margin-right:4px" />重新问诊</el-button>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'

const router = useRouter()
const list = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    list.value = await api.get('/consultation/registration/my')
  } finally {
    loading.value = false
  }
})

function statusType(s) {
  const map = { '已预约': '', '等待中': 'warning', '已就诊': 'success', '已过号': 'danger', '已取消': 'info' }
  return map[s] || ''
}
</script>

<style scoped>
.reg-list-page { max-width: 800px; margin: 10px auto; padding: 0 16px; }
.nav-bar { display: flex; justify-content: space-between; margin-bottom: 8px; }

@media (max-width: 768px) {
  .reg-list-page { padding: 0 8px; margin: 6px auto; }
  .nav-bar { flex-wrap: wrap; gap: 4px; justify-content: center; }
  .reg-list-page :deep(.el-table) { font-size: 13px; }
  .reg-list-page :deep(.el-table__body-wrapper) { overflow-x: auto; }
}
</style>
