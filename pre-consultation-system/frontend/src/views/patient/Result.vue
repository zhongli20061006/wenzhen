<template>
  <div class="result-page">
    <div class="nav-bar">
      <el-button text @click="$router.push({ name: 'Consultation' })"><ArrowLeft />返回问诊</el-button>
      <el-button text @click="$router.push({ name: 'RegistrationConfirm' })"><DocumentAdd />直接挂号</el-button>
      <el-button text @click="$router.push({ name: 'Profile' })"><User />个人中心</el-button>
    </div>

    <!-- 对话记录 -->
    <el-collapse v-model="activeHistory" class="history-collapse">
      <el-collapse-item name="history">
        <template #title>
          <span class="collapse-title"><ChatLineRound style="margin-right:4px" />{{ activeHistory.includes('history') ? '收起对话记录' : '展开对话记录' }}</span>
        </template>
        <el-timeline class="history-timeline">
          <el-timeline-item
            v-for="(msg, idx) in store.messages"
            :key="idx"
            :color="msg.role === 'system' ? '#909399' : '#67c23a'"
            :timestamp="msg.role === 'system' ? 'AI 问诊' : '我的回答'"
            placement="top"
            size="small"
          >
            <div class="msg-body">
              <div class="msg-text">{{ msg.text }}</div>
              <el-button
                v-if="msg.role === 'system' && msg.reasoning"
                text
                size="small"
                type="primary"
                class="reasoning-toggle"
                @click.stop="toggleReasoning(idx)"
              >
                <View v-if="!expandedReasoning.has(idx)" style="margin-right:2px;width:1em;height:1em" /><Hide v-else style="margin-right:2px;width:1em;height:1em" />
                {{ expandedReasoning.has(idx) ? '收起推理过程' : '查看推理过程' }}
              </el-button>
              <div v-if="expandedReasoning.has(idx) && msg.reasoning" class="reasoning-box">
                <pre>{{ msg.reasoning }}</pre>
              </div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </el-collapse-item>
    </el-collapse>

    <el-card>
      <template #header><h2>预问诊推荐结果</h2></template>
      <div v-if="loading" v-loading="true" style="min-height:120px" />
      <div v-else-if="result">
        <el-alert v-for="w in (result.warnings||[])" :key="w" :title="w" type="warning" show-icon :closable="false" style="margin-bottom:12px"><template #icon><WarningFilled /></template></el-alert>
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
          去挂号<Right style="margin-left:4px" />
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
import { ref, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useConsultationStore } from '../../stores/consultation'

const route = useRoute()
const router = useRouter()
const store = useConsultationStore()
const loading = ref(true)
const result = ref(null)

// 对话记录折叠状态
const activeHistory = ref([])
const expandedReasoning = reactive(new Set())
function toggleReasoning(idx) {
  if (expandedReasoning.has(idx)) {
    expandedReasoning.delete(idx)
  } else {
    expandedReasoning.add(idx)
  }
}

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

/* 对话记录 */
.history-collapse { margin-bottom: 12px; }
.history-collapse :deep(.el-collapse-item__header) { padding-left: 12px; font-weight: 500; }
.history-collapse :deep(.el-collapse-item__content) { padding-bottom: 0; }
.collapse-title { font-size: 14px; color: #606266; }
.history-timeline { padding: 8px 0 0; }
.history-timeline :deep(.el-timeline-item__timestamp) { font-size: 12px; color: #909399; }
.history-timeline :deep(.el-timeline-item__content) { font-size: 13px; }
.msg-body { line-height: 1.6; }
.msg-text { color: #303133; word-break: break-word; }
.reasoning-toggle { padding: 0; margin-top: 4px; }
.reasoning-box {
  margin-top: 6px;
  padding: 8px 10px;
  background: #f5f7fa;
  border-radius: 4px;
  border-left: 3px solid #dcdfe6;
}
.reasoning-box pre {
  margin: 0;
  font-size: 12px;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
}

@media (max-width: 768px) {
  .result-page { padding: 0 8px; margin: 6px auto; }
  .nav-bar { flex-wrap: wrap; gap: 4px; }
  .rec-header { flex-wrap: wrap; gap: 8px; }
  .rec-department { font-size: 16px; }
  .rec-reason { font-size: 13px; }
  .rec-diseases { font-size: 12px; }
  .el-button--primary { min-height: 44px; }
}
</style>
