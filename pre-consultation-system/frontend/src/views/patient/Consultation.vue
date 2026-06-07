<template>
  <div class="consultation-page">
    <div class="nav-bar">
      <el-button text @click="$router.push({ name: 'RegistrationConfirm' })">直接挂号</el-button>
      <el-button text @click="$router.push({ name: 'MyRegistrations' })">我的挂号</el-button>
      <el-button text @click="$router.push({ name: 'Profile' })">个人中心</el-button>
    </div>
    <el-card class="chat-card">
      <template #header>
        <div class="chat-header">
          <span>智能预问诊</span>
          <el-button text type="danger" @click="confirmReset">重新开始</el-button>
        </div>
      </template>

      <div v-if="!started" class="input-section">
        <el-form :model="form" label-position="top">
          <el-form-item label="请描述您的症状（多个症状用逗号分隔）">
            <el-input v-model="form.symptoms" type="textarea" :rows="3" placeholder="例如：头痛、发烧、咳嗽" />
          </el-form-item>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="不适持续了多久">
                <el-input v-model="form.duration" placeholder="如：3天、1周、2个月" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="疼痛程度（1-10）">
                <el-slider v-model="form.severity" :min="1" :max="10" show-input />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="既往病史（可选）">
            <el-input v-model="form.medical_history" placeholder="如：高血压、糖尿病" />
          </el-form-item>
          <el-form-item label="正在服用的药物（可选）">
            <el-input v-model="form.medications" placeholder="如：阿司匹林" />
          </el-form-item>
          <el-form-item label="过敏史（可选）">
            <el-input v-model="form.allergies" placeholder="如：青霉素" />
          </el-form-item>
          <el-button type="primary" @click="startChat" :loading="store.loading" style="width:100%">
            开始预问诊
          </el-button>
        </el-form>
      </div>

      <div v-else class="chat-section">
        <div class="round-info">第 {{ store.round }} / {{ store.totalRounds }} 轮</div>
        <div class="messages" ref="msgRef">
          <div v-for="(msg, i) in store.messages" :key="i" :class="['msg', msg.role]">
            <div class="bubble">{{ msg.text }}</div>
            <div v-if="msg.role === 'system' && msg.symptom_id" class="actions">
              <el-button size="small" @click="handleAnswer(msg.symptom_id, 'YES')" :disabled="answering">有</el-button>
              <el-button size="small" @click="handleAnswer(msg.symptom_id, 'NO')" :disabled="answering">没有</el-button>
              <el-button size="small" @click="handleAnswer(msg.symptom_id, 'UNKNOWN')" :disabled="answering">不确定</el-button>
            </div>
          </div>
          <div v-if="store.loading" class="msg system">
            <div class="bubble thinking">正在分析...</div>
          </div>
        </div>
      </div>

      <div v-if="store.result" class="result-section">
        <el-alert title="问诊完成，请查看推荐结果" type="success" show-icon :closable="false" />
        <el-button type="primary" @click="goResult" style="margin-top:12px">查看推荐结果</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useConsultationStore } from '../../stores/consultation'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const store = useConsultationStore()
const msgRef = ref(null)
const answering = ref(false)
const started = ref(false)

const form = reactive({
  symptoms: '',
  duration: '',
  severity: 5,
  medical_history: '',
  medications: '',
  allergies: '',
})

async function startChat() {
  if (!form.symptoms.trim()) return
  const symptoms = form.symptoms.split(/[,，、]+/).filter(Boolean).map(s => s.trim()).filter(Boolean)
  if (!symptoms.length) return
  await store.start(symptoms, {
    duration: form.duration || undefined,
    severity: form.severity,
    medical_history: form.medical_history ? form.medical_history.split(/[,，、]+/).filter(Boolean) : [],
    current_medications: form.medications ? form.medications.split(/[,，、]+/).filter(Boolean) : [],
    allergies: form.allergies ? form.allergies.split(/[,，、]+/).filter(Boolean) : [],
  })
  started.value = true
}

async function handleAnswer(symptomId, answer) {
  answering.value = true
  try {
    await store.answer(symptomId, answer)
  } finally {
    answering.value = false
  }
}

function goResult() {
  router.push({ name: 'Result', params: { id: store.sessionId } })
}

function goRegistrations() {
  router.push({ name: 'MyRegistrations' })
}

async function confirmReset() {
  try {
    await ElMessageBox.confirm('确定要重新开始吗？当前问诊进度将丢失。', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    store.reset()
    started.value = false
    form.symptoms = ''
    form.duration = ''
    form.severity = 5
    form.medical_history = ''
    form.medications = ''
    form.allergies = ''
  } catch {}
}

watch(() => store.messages.length, () => {
  nextTick(() => {
    if (msgRef.value) msgRef.value.scrollTop = msgRef.value.scrollHeight
  })
})
</script>

<style scoped>
.consultation-page { max-width: 700px; margin: 10px auto; padding: 0 16px; }
.nav-bar { display: flex; justify-content: flex-end; margin-bottom: 8px; }
.chat-card { min-height: 600px; }
.chat-header { display: flex; justify-content: space-between; align-items: center; }
.input-section { padding: 16px 0; }
.chat-section { display: flex; flex-direction: column; }
.round-info { text-align: center; color: #999; font-size: 13px; margin-bottom: 8px; }
.messages { max-height: 450px; overflow-y: auto; padding: 12px 0; }
.msg { margin-bottom: 16px; }
.msg.system { text-align: left; }
.msg.user { text-align: right; }
.bubble { display: inline-block; padding: 10px 16px; border-radius: 12px; max-width: 80%; }
.msg.system .bubble { background: #f0f2f5; }
.msg.user .bubble { background: #409eff; color: #fff; }
.msg.user .bubble.thinking { background: #e8e8e8; color: #999; }
.actions { margin-top: 8px; display: flex; gap: 8px; }
.result-section { margin-top: 16px; padding: 16px 0; }
</style>
