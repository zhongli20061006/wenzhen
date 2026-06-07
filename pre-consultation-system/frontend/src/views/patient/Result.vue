<template>
  <div class="result-page">
    <div class="nav-bar">
      <el-button text @click="$router.push({ name: 'Consultation' })">返回问诊</el-button>
      <el-button text @click="$router.push({ name: 'RegistrationConfirm' })">直接挂号</el-button>
      <el-button text @click="$router.push({ name: 'Profile' })">个人中心</el-button>
    </div>
    <el-card>
      <template #header><h2>预问诊推荐结果</h2></template>
      <div v-if="loading" v-loading="true" style="min-height:120px" />
      <div v-else-if="result">
        <el-alert v-for="w in (result.warnings||[])" :key="w" :title="w" type="warning" show-icon :closable="false" style="margin-bottom:12px" />
        <div v-for="rec in (result.recommendations||[])" :key="rec.rank" class="rec-card">
          <el-card shadow="hover">
            <div class="rec-header">
              <el-tag type="danger" v-if="rec.rank === 1">推荐</el-tag>
              <span class="rec-department">{{ rec.department }}</span>
              <el-tag :type="urgencyType(rec.urgency)">{{ rec.urgency }}</el-tag>
            </div>
            <p class="rec-reason">{{ rec.reason }}</p>
            <p class="rec-diseases">考虑疾病：{{ (rec.diseases_considered||[]).join('、') }}</p>
          </el-card>
        </div>
        <el-button type="primary" @click="goRegistration" style="margin-top:16px;width:100%">
          去挂号
        </el-button>
      </div>
      <div v-else class="empty">
        <el-empty description="暂无可用的推荐结果" />
        <el-button @click="$router.push({ name: 'Consultation' })">重新问诊</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useConsultationStore } from '../../stores/consultation'

const route = useRoute()
const router = useRouter()
const store = useConsultationStore()
const loading = ref(true)
const result = ref(null)

onMounted(async () => {
  try {
    if (store.result) {
      result.value = store.result
    } else if (route.params.id) {
      store.sessionId = route.params.id
      const res = await store.getResult()
      result.value = res.result
    }
  } finally {
    loading.value = false
  }
})

function urgencyType(u) {
  if (!u) return 'info'
  if (u.includes('立即')) return 'danger'
  if (u.includes('近期')) return 'warning'
  return 'info'
}

function goRegistration() {
  const top = result.value?.recommendations?.[0]
  router.push({
    name: 'RegistrationConfirm',
    query: {
      consultation_id: store.sessionId,
      department: top?.department || '',
      department_id: top?.department_id || '',
    },
  })
}
</script>

<style scoped>
.result-page { max-width: 700px; margin: 10px auto; padding: 0 16px; }
.nav-bar { display: flex; justify-content: flex-start; margin-bottom: 8px; }
.rec-card { margin-bottom: 12px; }
.rec-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.rec-department { font-size: 18px; font-weight: bold; }
.rec-reason { color: #666; margin-bottom: 4px; }
.rec-diseases { color: #999; font-size: 13px; }
.empty { text-align: center; padding: 40px 0; }
</style>
