import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useConsultationStore = defineStore('consultation', () => {
  const sessionId = ref('')
  const messages = ref([])
  const result = ref(null)
  const loading = ref(false)
  const round = ref(0)
  const totalRounds = ref(5)

  async function start(symptoms, data) {
    loading.value = true
    try {
      const res = await api.post('/consultation/start', {
        symptoms,
        ...data,
      })
      sessionId.value = res.consultation_id
      if (res.question_text) {
        messages.value.push({ role: 'system', text: res.question_text, symptom_id: res.symptom_id, reasoning: res.ds_reasoning || '' })
        round.value = 1
        totalRounds.value = res.total_rounds || 5
      } else if (res.result) {
        result.value = res.result
      }
    } finally {
      loading.value = false
    }
  }

  async function answer(symptomId, answer) {
    loading.value = true
    try {
      const res = await api.post(`/consultation/${sessionId.value}/answer`, {
        symptom_id: symptomId,
        answer,
      })
      messages.value.push({ role: 'user', text: answer === 'YES' ? '是' : answer === 'NO' ? '否' : '不确定' })
      if (res.status === 'QUESTIONING') {
        messages.value.push({ role: 'system', text: res.question_text, symptom_id: res.symptom_id, reasoning: res.ds_reasoning || '' })
        round.value = res.round
      } else if (res.result) {
        result.value = res.result
      }
    } finally {
      loading.value = false
    }
  }

  async function getResult() {
    const res = await api.get(`/consultation/${sessionId.value}/result`)
    result.value = res.result
    return res
  }

  function reset() {
    sessionId.value = ''
    messages.value = []
    result.value = null
    round.value = 0
    totalRounds.value = 5
  }

  return { sessionId, messages, result, loading, round, totalRounds, start, answer, getResult, reset }
})
