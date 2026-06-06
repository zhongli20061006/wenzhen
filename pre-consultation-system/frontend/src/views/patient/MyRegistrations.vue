<template>
  <div class="my-reg-page">
    <el-card>
      <template #header><h2>我的挂号记录</h2></template>
      <el-table :data="list" v-loading="loading" stripe style="width:100%">
        <el-table-column prop="registration_date" label="日期" width="120" />
        <el-table-column prop="time_slot" label="时段" width="80" />
        <el-table-column prop="department" label="科室" />
        <el-table-column prop="doctor" label="医生" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-button @click="$router.push('/consultation')" style="margin-top:12px">重新问诊</el-button>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api'

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
.my-reg-page { max-width: 800px; margin: 20px auto; padding: 0 16px; }
</style>
