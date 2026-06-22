<template>
  <div class="consultation-page">
    <div class="nav-bar">
      <el-button text @click="$router.push({ name: 'RegistrationConfirm' })">
        <el-icon><DocumentAdd /></el-icon> 直接挂号
      </el-button>
      <el-button text @click="$router.push({ name: 'MyRegistrations' })">
        <el-icon><List /></el-icon> 我的挂号
      </el-button>
      <el-button text @click="$router.push({ name: 'Profile' })">
        <el-icon><User /></el-icon> 个人中心
      </el-button>
    </div>
    <el-card class="chat-card">
      <template #header>
        <div class="chat-header">
          <div class="chat-header-title">
            <el-icon class="header-icon"><ChatDotRound /></el-icon>
            <span>智能预问诊</span>
          </div>
          <el-button text type="danger" @click="confirmReset">
            <el-icon><RefreshRight /></el-icon> 重新开始
          </el-button>
        </div>
      </template>

      <div v-if="!started" class="input-section">
        <el-form :model="form" label-position="top">
          <el-form-item label="请描述您的不适">
            <el-input v-model="form.description" type="textarea" :rows="4" placeholder="用您自己的话描述不适，例如：最近几天一直头疼，还有点发烧，咳嗽的时候胸口会痛&#10;&#10;系统会自动从描述中识别症状关键词" />
          </el-form-item>

          <el-collapse v-model="showAdvanced">
            <el-collapse-item name="1">
              <template #title>
                <div class="collapse-title">
                  <el-icon><Setting /></el-icon>
                  <span>高级：添加具体症状</span>
                </div>
              </template>
              <el-form-item label="症状（多个用逗号分隔）">
                <el-input v-model="form.symptoms" placeholder="例如：头痛、发烧、咳嗽" />
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
            </el-collapse-item>
          </el-collapse>

          <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon :closable="false" class="error-alert" />
          <el-button type="primary" @click="startChat" :loading="store.loading" class="start-btn" :disabled="!canStart || store.loading">
            开始预问诊
          </el-button>
        </el-form>
      </div>

      <div v-else class="chat-section">
        <div class="round-info"><span>第 {{ store.round }} / {{ store.totalRounds }} 轮</span></div>
        <div class="messages" ref="msgRef">
          <div v-for="(msg, i) in store.messages" :key="i" :class="['msg', msg.role]">
            <template v-if="msg.role === 'system'">
              <div class="msg-avatar">
                <el-icon><Service /></el-icon>
              </div>
              <div class="msg-content-wrapper">
                <div class="bubble">{{ msg.text }}</div>
                <div v-if="msg.reasoning" class="reasoning-box">
                  <el-icon class="reasoning-icon"><InfoFilled /></el-icon>
                  <span>AI 追问理由：{{ msg.reasoning }}</span>
                </div>
                <div v-if="msg.symptom_id" class="actions">
                  <el-button size="small" round @click="handleAnswer(msg.symptom_id, 'YES')" :disabled="answering || store.loading">
                    <el-icon><Check /></el-icon> 有
                  </el-button>
                  <el-button size="small" round @click="handleAnswer(msg.symptom_id, 'NO')" :disabled="answering || store.loading">
                    <el-icon><Close /></el-icon> 没有
                  </el-button>
                  <el-button size="small" round @click="handleAnswer(msg.symptom_id, 'UNKNOWN')" :disabled="answering || store.loading">
                    <el-icon><QuestionFilled /></el-icon> 不确定
                  </el-button>
                </div>
              </div>
            </template>
            <template v-else>
              <div class="msg-content-wrapper msg-user-wrapper">
                <div class="bubble">{{ msg.text }}</div>
              </div>
            </template>
          </div>
          <div v-if="store.loading" class="msg system">
            <div class="msg-avatar">
              <el-icon><Service /></el-icon>
            </div>
            <div class="msg-content-wrapper">
              <div class="bubble thinking">
                <div class="typing-indicator"><span></span><span></span><span></span></div>
                <span class="typing-text">AI 正在分析您的症状</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="store.result" class="result-section">
        <el-alert title="问诊完成，请查看推荐结果" type="success" show-icon :closable="false" />
        <el-button type="primary" @click="goResult" class="result-btn">
          查看推荐结果 <el-icon><Right /></el-icon>
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useConsultationStore } from '../../stores/consultation'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const store = useConsultationStore()
const msgRef = ref(null)
const answering = ref(false)
const started = ref(false)
const showAdvanced = ref([])
const errorMsg = ref('')

const form = reactive({
  description: '',
  symptoms: '',
  duration: '',
  severity: 5,
  medical_history: '',
  medications: '',
  allergies: '',
})

const canStart = computed(() => form.description.trim() || form.symptoms.trim())

async function startChat() {
  if (!canStart.value || store.loading) return
  errorMsg.value = ''
  const symptoms = form.symptoms.split(/[,，、]+/).filter(Boolean).map(s => s.trim()).filter(Boolean)
  started.value = true
  try {
    await store.start(symptoms, {
      description: form.description.trim() || undefined,
      duration: form.duration || undefined,
      severity: form.severity,
      medical_history: form.medical_history ? form.medical_history.split(/[,，、]+/).filter(Boolean) : [],
      current_medications: form.medications ? form.medications.split(/[,，、]+/).filter(Boolean) : [],
      allergies: form.allergies ? form.allergies.split(/[,，、]+/).filter(Boolean) : [],
    })
  } catch (e) {
    errorMsg.value = e?.response?.data?.detail || '问诊启动失败，请稍后重试'
    started.value = false
  }
}

async function handleAnswer(symptomId, answer) {
  if (answering.value) return
  answering.value = true
  errorMsg.value = ''
  try {
    await store.answer(symptomId, answer)
  } catch (e) {
    errorMsg.value = e?.response?.data?.detail || '回答提交失败，请稍后重试'
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
    form.description = ''
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
/* ===== Page Layout ===== */
.consultation-page {
  max-width: 700px;
  margin: 10px auto;
  padding: 0 16px;
  min-height: 100vh;
  background: linear-gradient(180deg, #F0F4F8 0%, #E8EEF4 100%);
}

/* ===== Navigation Bar ===== */
.nav-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
  padding-bottom: 12px;
  gap: 4px;
  border-bottom: 1px solid var(--color-border, #E2E8F0);
}

.nav-bar .el-button {
  border-radius: 20px;
  padding: 8px 16px;
  font-size: 13px;
  color: var(--color-text-secondary, #64748B);
  gap: 4px;
  transition: all var(--transition-fast, 0.2s);
}

.nav-bar .el-button:hover {
  background: var(--color-bg, #F1F5F9);
  color: var(--color-primary, #1E6FFF);
}

/* ===== Chat Card ===== */
.chat-card {
  border-radius: var(--radius-lg, 16px);
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0,0,0,0.08));
  border: 1px solid var(--color-border, #E2E8F0);
  min-height: 600px;
}

.chat-card :deep(.el-card__body) {
  padding: 20px 24px;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1E293B);
}

.header-icon {
  font-size: 20px;
  color: var(--color-primary, #1E6FFF);
}

/* ===== Input Section ===== */
.input-section {
  padding: 16px 0;
}

.input-section .el-textarea__inner {
  border-radius: 8px;
  min-height: 100px;
  font-size: 14px;
  line-height: 1.6;
  transition: border-color var(--transition-fast, 0.2s), box-shadow var(--transition-fast, 0.2s);
}

.input-section .el-textarea__inner:focus {
  border-color: var(--color-primary, #1E6FFF);
  box-shadow: 0 0 0 3px rgba(30, 111, 255, 0.1);
}

.input-section .el-textarea__inner::placeholder {
  color: var(--color-text-muted, #94A3B8);
  font-size: 13px;
}

.collapse-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}

.error-alert {
  margin-bottom: 12px;
}

.start-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  border: none;
  background: linear-gradient(135deg, var(--color-primary, #1E6FFF), #4D94FF);
  border-radius: 10px;
  letter-spacing: 0.5px;
  transition: all var(--transition-normal, 0.3s);
}

.start-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(30, 111, 255, 0.35);
}

.start-btn:active {
  transform: translateY(0);
}

.start-btn:disabled {
  opacity: 0.5;
  background: var(--color-primary, #1E6FFF);
  transform: none;
  box-shadow: none;
}

/* ===== Chat Section ===== */
.chat-section {
  display: flex;
  flex-direction: column;
}

.round-info {
  text-align: center;
  margin-bottom: 16px;
}

.round-info span {
  display: inline-block;
  background: #E2E8F0;
  color: var(--color-text-secondary, #64748B);
  font-size: 12px;
  font-weight: 500;
  padding: 4px 14px;
  border-radius: 20px;
  letter-spacing: 0.3px;
}

/* ===== Messages Container ===== */
.messages {
  min-height: 400px;
  max-height: 500px;
  overflow-y: auto;
  padding: 12px 4px;
  scroll-behavior: smooth;
}

/* ===== Individual Message ===== */
.msg {
  display: flex;
  margin-bottom: 20px;
  gap: 10px;
  align-items: flex-start;
  animation: slideInUp 0.3s ease-out both;
}

.msg.system {
  justify-content: flex-start;
}

.msg.user {
  justify-content: flex-end;
}

/* ===== Message Avatar ===== */
.msg-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #E2E8F0, #CBD5E1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 15px;
  color: var(--color-text-secondary, #64748B);
  margin-top: 6px;
}

/* ===== Message Content ===== */
.msg-content-wrapper {
  max-width: 75%;
  display: flex;
  flex-direction: column;
}

.msg.user .msg-content-wrapper {
  align-items: flex-end;
}

/* ===== Bubble ===== */
.bubble {
  display: inline-block;
  padding: 10px 16px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}

.msg.system .bubble {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 16px 16px 16px 4px;
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.04));
  color: var(--color-text-primary, #1E293B);
}

.msg.user .bubble {
  background: linear-gradient(135deg, #1E6FFF, #4D94FF);
  color: #FFFFFF;
  border-radius: 16px 16px 4px 16px;
  box-shadow: 0 2px 8px rgba(30, 111, 255, 0.2);
}

/* ===== Thinking / Loading Bubble ===== */
.bubble.thinking {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 16px 16px 16px 4px;
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.04));
  padding: 12px 18px;
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
}

.typing-indicator span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-primary, #1E6FFF);
  animation: bounce-dots 1.4s ease-in-out infinite both;
}

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

.typing-text {
  font-size: 13px;
  color: var(--color-text-secondary, #64748B);
}

/* ===== Reasoning Box ===== */
.reasoning-box {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 8px;
  background: #EFF6FF;
  border-left: 3px solid #93C5FD;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--color-text-secondary, #64748B);
  line-height: 1.5;
}

.reasoning-icon {
  flex-shrink: 0;
  font-size: 14px;
  color: #60A5FA;
  margin-top: 1px;
}

/* ===== Action Buttons ===== */
.actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.actions .el-button {
  border-radius: 20px;
  min-width: 64px;
  font-size: 13px;
  transition: all var(--transition-fast, 0.2s);
}

.actions .el-button:hover {
  transform: scale(1.05);
}

.actions .el-button--small {
  padding: 6px 14px;
  height: 32px;
}

/* YES button */
.actions .el-button:nth-child(1) {
  --el-button-bg-color: #ECFDF5;
  --el-button-border-color: #A7F3D0;
  --el-button-text-color: #059669;
  --el-button-hover-bg-color: #D1FAE5;
  --el-button-hover-border-color: #6EE7B7;
  --el-button-hover-text-color: #047857;
  --el-button-active-bg-color: #A7F3D0;
  --el-button-active-border-color: #34D399;
}

/* NO button */
.actions .el-button:nth-child(2) {
  --el-button-bg-color: #FEF2F2;
  --el-button-border-color: #FECACA;
  --el-button-text-color: #DC2626;
  --el-button-hover-bg-color: #FEE2E2;
  --el-button-hover-border-color: #FCA5A5;
  --el-button-hover-text-color: #B91C1C;
  --el-button-active-bg-color: #FECACA;
  --el-button-active-border-color: #F87171;
}

/* UNKNOWN button */
.actions .el-button:nth-child(3) {
  --el-button-bg-color: #FFFBEB;
  --el-button-border-color: #FDE68A;
  --el-button-text-color: #D97706;
  --el-button-hover-bg-color: #FEF3C7;
  --el-button-hover-border-color: #FCD34D;
  --el-button-hover-text-color: #B45309;
  --el-button-active-bg-color: #FDE68A;
  --el-button-active-border-color: #FBBF24;
}

/* ===== Result Section ===== */
.result-section {
  margin-top: 16px;
  padding: 16px 0;
}

.result-btn {
  width: 100%;
  height: 48px;
  font-size: 15px;
  font-weight: 600;
  border: none;
  background: linear-gradient(135deg, var(--color-primary, #1E6FFF), #4D94FF);
  border-radius: 10px;
  margin-top: 12px;
  letter-spacing: 0.5px;
  gap: 6px;
  transition: all var(--transition-normal, 0.3s);
}

.result-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(30, 111, 255, 0.35);
}

/* ===== Animations ===== */
@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes bounce-dots {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* ===== Custom Scrollbar ===== */
.messages::-webkit-scrollbar {
  width: 6px;
}

.messages::-webkit-scrollbar-track {
  background: transparent;
}

.messages::-webkit-scrollbar-thumb {
  background: #CBD5E1;
  border-radius: 3px;
}

.messages::-webkit-scrollbar-thumb:hover {
  background: #94A3B8;
}

/* ===== Responsive ===== */
@media (max-width: 768px) {
  .consultation-page {
    padding: 0 8px;
    margin: 6px auto;
  }

  .nav-bar {
    flex-wrap: wrap;
    gap: 4px;
    justify-content: center;
  }

  .chat-card {
    min-height: auto;
  }

  .chat-card :deep(.el-card__body) {
    padding: 12px;
  }

  .messages {
    min-height: 300px;
    max-height: 60vh;
    padding: 8px 4px;
  }

  .msg {
    margin-bottom: 16px;
  }

  .msg-content-wrapper {
    max-width: 85%;
  }

  .bubble {
    padding: 8px 14px;
    font-size: 14px;
  }

  .actions {
    gap: 6px;
  }

  .actions .el-button {
    min-height: 36px;
    flex: 1;
    min-width: 0;
    font-size: 12px;
  }

  .input-section {
    padding: 12px 0;
  }

  .input-section .el-button {
    min-height: 44px;
  }

  .round-info {
    font-size: 12px;
  }

  .round-info span {
    font-size: 11px;
    padding: 3px 12px;
  }

  .reasoning-box {
    font-size: 11px;
    padding: 6px 10px;
  }

  .msg-avatar {
    width: 24px;
    height: 24px;
    font-size: 13px;
  }
}
</style>
