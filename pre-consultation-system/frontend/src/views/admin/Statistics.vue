<template>
  <div class="admin-page">
    <el-container>
      <el-header>
        <div class="header-bar">
          <span>数据统计</span>
          <el-menu mode="horizontal" :ellipsis="false" router>
            <el-menu-item index="/admin/symptoms">症状</el-menu-item>
            <el-menu-item index="/admin/diseases">疾病</el-menu-item>
            <el-menu-item index="/admin/rules">规则</el-menu-item>
            <el-menu-item index="/admin/statistics">统计</el-menu-item>
          </el-menu>
          <el-button text @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main>
        <el-row :gutter="16">
          <el-col :span="6">
            <el-card>
              <p class="stat-num">{{ stats.total_consultations }}</p>
              <p class="stat-label">总问诊量</p>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card>
              <p class="stat-num">{{ stats.weekly_consultations }}</p>
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
  total_consultations: 0, weekly_consultations: 0,
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
</style>
