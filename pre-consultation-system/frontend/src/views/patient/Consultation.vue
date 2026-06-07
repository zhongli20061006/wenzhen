<template>
  <div class="consultation-page">
    <el-card class="chat-card">
      <template #header>
        <div class="chat-header">
          <span>智能预问诊</span>
          <div>
            <el-button text @click="$router.push('/profile')">个人中心</el-button>
            <el-button text @click="resetChat">重新开始</el-button>
          </div>
        </div>
      </template>

      <div v-if="!started" class="input-section">
        <el-form :model="form" label-position="top">
          <el-form-item label="请描述您的症状（多个症状用逗号分隔）">
            <el-input v-model="form.symptoms" type="textarea" :rows="3" placeholder="例如：头痛、发烧、咳嗽" />
          </el-form-item>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="发病日期">
                <el-date-picker v-model="form.onset_date" type="date" placeholder="选择日期" style="width:100%" />
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
        <div class="messages" ref="msgRef">
          <div v-for="(msg, i) in store.messages" :key="i" :class="['msg', msg.role]">
            <div class="bubble">{{ msg.text }}</div>
            <div v-if="msg.role === 'system' && msg.symptom_id" class="actions">
              <el-button size="small" type="primary" @click="handleAnswer(msg.symptom_id, 'YES')" :disabled="answering">
                有
              </el-button>
              <el-button size="small" @click="handleAnswer(msg.symptom_id, 'NO')" :disabled="answering">
                没有
              </el-button>
              <el-button size="small" @click="handleAnswer(msg.symptom_id, 'UNKNOWN')" :disabled="answering">
                不确定
              </el-button>
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

const router = useRouter()
const store = useConsultationStore()
const msgRef = ref(null)
const answering = ref(false)
const started = ref(false)

const form = reactive({
  symptoms: '',
  onset_date: null,
  severity: 5,
  medical_history: '',
  medications: '',
  allergies: '',
})

async function startChat() {
  if (!form.symptoms.trim()) return
  started.value = true
  const symptoms = form.symptoms.split(/[,，、\s]+/).filter(Boolean)
  await store.start(symptoms, {
    onset_date: form.onset_date || undefined,
    severity: form.severity,
    medical_history: form.medical_history ? form.medical_history.split(/[,，、\s]+/) : [],
    current_medications: form.medications ? form.medications.split(/[,，、\s]+/) : [],
    allergies: form.allergies ? form.allergies.split(/[,，、\s]+/) : [],
  })
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
  router.push(`/consultation/${store.sessionId}/result`)
}

function resetChat() {
  store.reset()
  started.value = false
}

watch(() => store.messages.length, () => {
  nextTick(() => {
    if (msgRef.value) msgRef.value.scrollTop = msgRef.value.scrollHeight
  })
})
</script>

<style scoped>
.consultation-page { max-width: 700px; margin: 20px auto; padding: 0 16px; }
.chat-card { min-height: 600px; }
.chat-header { display: flex; justify-content: space-between; align-items: center; }
.input-section { padding: 16px 0; }
.chat-section { display: flex; flex-direction: column; }
.messages { max-height: 500px; overflow-y: auto; padding: 12px 0; }
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
