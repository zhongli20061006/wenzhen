<template>
  <div class="admin-page">
    <el-container>
      <el-header>
        <div class="header-bar">
          <span><DataLine style="margin-right:6px" />数据统计</span>
          <el-menu mode="horizontal" :ellipsis="false" router>
            <el-menu-item index="/admin/symptoms"><Memo />症状</el-menu-item>
            <el-menu-item index="/admin/diseases"><Collection />疾病</el-menu-item>
            <el-menu-item index="/admin/rules"><SetUp />规则</el-menu-item>
            <el-menu-item index="/admin/statistics"><DataLine />统计</el-menu-item>
          </el-menu>
          <el-button text @click="logout"><SwitchButton />退出</el-button>
        </div>
      </el-header>
      <el-main>
        <el-row :gutter="16">
          <el-col :span="6">
            <el-card>
              <p class="stat-num">{{ stats.total_sessions }}</p>
              <p class="stat-label">总问诊量</p>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card>
              <p class="stat-num">{{ stats.weekly_sessions }}</p>
              <p class="stat-label">本周问诊量</p>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card>
              <p class="stat-num">{{ (stats.accuracy * 100).toFixed(1) }}%</p>
              <p class="stat-label">推荐准确率</p>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card>
              <p class="stat-num">{{ stats.total_feedback }}</p>
              <p class="stat-label">反馈总数</p>
            </el-card>
          </el-col>
        </el-row>

        <el-card style="margin-top:16px">
          <template #header>反馈详情</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="正确推荐">{{ stats.correct_count }}</el-descriptions-item>
            <el-descriptions-item label="错误推荐">{{ stats.incorrect_count }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'
import api from '../../api'

const router = useRouter()
const store = useUserStore()
const stats = ref({
  total_sessions: 0, total_registrations: 0,
  weekly_sessions: 0,
  accuracy: 0, total_feedback: 0, correct_count: 0, incorrect_count: 0,
})

onMounted(async () => { stats.value = await api.get('/admin/statistics') })
function logout() { store.logout(); router.push('/login') }
</script>

<style scoped>
.admin-page { max-width: 1000px; margin: 0 auto; }
.header-bar { display: flex; justify-content: space-between; align-items: center; }
.stat-num { font-size: 32px; font-weight: bold; color: #409eff; text-align: center; }
.stat-label { text-align: center; color: #666; margin-top: 8px; }

@media (max-width: 768px) {
  .admin-page { max-width: 100%; }
  .admin-page :deep(.el-header) { height: auto !important; padding: 8px; }
  .header-bar { flex-wrap: wrap; gap: 6px; }
  .header-bar > span { font-size: 16px; width: 100%; }
  .header-bar .el-menu { width: 100%; overflow-x: auto; }
  .header-bar .el-menu .el-menu-item { padding: 0 10px; font-size: 13px; }
  .admin-page :deep(.el-main) { padding: 8px; }
  .admin-page :deep(.el-row) { display: flex; flex-direction: column; gap: 8px; }
  .admin-page :deep(.el-col) { width: 100% !important; max-width: 100%; }
  .stat-num { font-size: 24px; }
  .admin-page :deep(.el-descriptions__cell) { padding: 8px; font-size: 13px; }
}
</style>
