<template>
  <div class="feedback-page">
    <div class="nav-bar">
      <el-button text @click="$router.push({ name: 'TodayPatients' })"><ArrowLeft />返回工作台</el-button>
      <el-button text @click="$router.push({ name: 'Profile' })"><User />个人中心</el-button>
    </div>
    <el-card v-if="stats">
      <template #header><h2><PieChart style="margin-right:6px" />反馈统计</h2></template>
      <el-row :gutter="20">
        <el-col :span="6">
          <el-statistic title="总反馈数" :value="stats.total" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="正确数" :value="stats.correct" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="错误数" :value="stats.incorrect" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="准确率" :value="(stats.accuracy * 100).toFixed(1) + '%'" />
        </el-col>
      </el-row>
    </el-card>
    <el-card style="margin-top:16px" v-if="stats?.by_department?.length">
      <template #header><h2><TrendCharts style="margin-right:6px" />按科室准确率</h2></template>
      <div v-for="d in stats.by_department" :key="d.department_id" class="dept-row">
        <span class="dept-name">{{ d.department_name }}</span>
        <el-progress :percentage="d.accuracy * 100" :format="() => d.correct + '/' + d.total" :color="d.accuracy >= 0.8 ? '#67c23a' : d.accuracy >= 0.5 ? '#e6a23c' : '#f56c6c'" style="flex:1;margin:0 12px" />
      </div>
    </el-card>
    <el-card style="margin-top:16px">
      <template #header><h2><List style="margin-right:6px" />反馈记录</h2></template>
      <el-table :data="list" stripe v-loading="loading">
        <el-table-column prop="id" label="编号" width="60" />
        <el-table-column prop="patient_id" label="患者" width="100" />
        <el-table-column prop="date" label="日期" width="100" />
        <el-table-column prop="recommended_dept" label="推荐科室" />
        <el-table-column prop="actual_dept" label="实际科室" />
        <el-table-column label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_correct ? 'success' : 'danger'">{{ row.is_correct ? '正确' : '错误' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="error_reason" label="错误原因" width="90" />
        <el-table-column prop="doctor_note" label="备注" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'

const router = useRouter()
const list = ref([])
const stats = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const [data, accuracy] = await Promise.all([
      api.get('/doctor/feedback-history'),
      api.get('/doctor/accuracy'),
    ])
    list.value = data
    stats.value = accuracy
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.feedback-page { max-width: 900px; margin: 10px auto; padding: 0 16px; }
.nav-bar { display: flex; justify-content: space-between; margin-bottom: 8px; }
.dept-row { display: flex; align-items: center; padding: 6px 0; }
.dept-name { width: 100px; font-size: 14px; }

@media (max-width: 768px) {
  .feedback-page { padding: 0 8px; margin: 6px auto; }
  .nav-bar { flex-wrap: wrap; gap: 4px; }
  .feedback-page :deep(.el-row) { display: flex; flex-direction: column; gap: 8px; }
  .feedback-page :deep(.el-col) { width: 100% !important; max-width: 100%; }
  .feedback-page :deep(.el-statistic) { text-align: center; }
  .dept-row { flex-wrap: wrap; gap: 8px; }
  .dept-name { width: auto; font-size: 13px; }
  .dept-row .el-progress { margin: 0 !important; width: 100%; }
  .feedback-page :deep(.el-table) { font-size: 13px; }
  .feedback-page :deep(.el-table__body-wrapper) { overflow-x: auto; }
  .feedback-page :deep(.el-table .el-table__cell) { white-space: nowrap; }
}
</style>
