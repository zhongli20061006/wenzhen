<template>
  <div class="report-page">
    <el-card v-loading="loading">
      <template #header>
        <div class="header-bar">
          <span>预问诊报告</span>
          <el-button @click="$router.push('/doctor/today')">返回</el-button>
        </div>
      </template>

      <div v-if="report">
        <el-descriptions title="挂号信息" :column="2" border>
          <el-descriptions-item label="患者">{{ report.registration.patient_id }}</el-descriptions-item>
          <el-descriptions-item label="科室">{{ report.registration.department }}</el-descriptions-item>
          <el-descriptions-item label="医生">{{ report.registration.doctor }}</el-descriptions-item>
          <el-descriptions-item label="日期">{{ report.registration.date }} {{ report.registration.time_slot }}</el-descriptions-item>
        </el-descriptions>

        <el-divider />

        <el-descriptions title="系统推荐" :column="1" border v-if="report.consultation?.recommendation">
          <el-descriptions-item label="推荐科室">
            {{ report.consultation.recommendation.recommendations?.[0]?.department }}
          </el-descriptions-item>
          <el-descriptions-item label="推荐理由">
            {{ report.consultation.recommendation.recommendations?.[0]?.reason }}
          </el-descriptions-item>
          <el-descriptions-item label="考虑疾病">
            {{ report.consultation.recommendation.recommendations?.[0]?.diseases_considered?.join('、') }}
          </el-descriptions-item>
          <el-descriptions-item label="警告">
            {{ report.consultation.recommendation.warnings?.join('；') || '无' }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider />

        <el-timeline v-if="report.dialog.length">
          <template #title><h3>问诊对话</h3></template>
          <el-timeline-item v-for="q in report.dialog" :key="q.round" :timestamp="`第${q.round}轮`">
            <p>问：{{ q.question }}</p>
            <p>答：<el-tag size="small">{{ q.answer }}</el-tag></p>
          </el-timeline-item>
        </el-timeline>

        <el-divider />

        <el-form :model="feedback" label-width="120px" v-if="!submitted">
          <h3>医生反馈</h3>
          <el-form-item label="推荐是否正确">
            <el-radio-group v-model="feedback.is_correct">
              <el-radio :value="true">正确</el-radio>
              <el-radio :value="false">不正确</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="实际科室" v-if="!feedback.is_correct">
            <el-select v-model="feedback.actual_department_id" placeholder="选择实际科室" filterable style="width:100%">
              <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="医生备注">
            <el-input v-model="feedback.doctor_note" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="submitFeedback" :loading="submitting">提交反馈</el-button>
          </el-form-item>
        </el-form>
        <el-alert v-else title="反馈已提交" type="success" show-icon :closable="false" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../api'

const route = useRoute()
const report = ref(null)
const loading = ref(true)
const submitting = ref(false)
const submitted = ref(false)
const departments = ref([])

const feedback = reactive({
  is_correct: true,
  actual_department_id: null,
  doctor_note: '',
})

onMounted(async () => {
  try {
    const id = route.params.id
    report.value = await api.get(`/doctor/patient/${id}/report`)
    departments.value = await api.get('/admin/departments')
  } finally {
    loading.value = false
  }
})

async function submitFeedback() {
  submitting.value = true
  try {
    await api.post('/doctor/feedback', {
      registration_id: report.value.registration.id,
      is_correct: feedback.is_correct,
      actual_department_id: feedback.is_correct
        ? report.value.registration.department_id
        : feedback.actual_department_id,
      doctor_note: feedback.doctor_note,
    })
    ElMessage.success('反馈提交成功')
    submitted.value = true
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.report-page { max-width: 800px; margin: 20px auto; padding: 0 16px; }
.header-bar { display: flex; justify-content: space-between; align-items: center; }
</style>
