<template>
  <div class="reg-page">
    <el-card>
      <template #header><h2>挂号确认</h2></template>
      <el-form :model="form" label-width="100px">
        <el-form-item label="科室">
          <el-input v-model="form.department_name" disabled />
        </el-form-item>
        <el-form-item label="医生">
          <el-select v-model="form.doctor_id" placeholder="请选择医生" style="width:100%">
            <el-option v-for="d in doctors" :key="d.id" :label="`${d.name} ${d.title || ''}`" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="就诊日期">
          <el-date-picker v-model="form.reg_date" type="date" :disabled-date="disabledDate" style="width:100%" />
        </el-form-item>
        <el-form-item label="就诊时段">
          <el-radio-group v-model="form.time_slot">
            <el-radio value="上午">上午</el-radio>
            <el-radio value="下午">下午</el-radio>
            <el-radio value="晚上">晚上</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="submit" :loading="submitting" style="width:100%">
            确认挂号
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../../api'
import { useConsultationStore } from '../../stores/consultation'

const route = useRoute()
const router = useRouter()
const store = useConsultationStore()
const doctors = ref([])
const submitting = ref(false)

const form = reactive({
  consultation_id: route.query.consultation_id || store.sessionId,
  department_name: route.query.department || '',
  department_id: null,
  doctor_id: null,
  reg_date: new Date(Date.now() + 86400000),
  time_slot: '上午',
})

onMounted(async () => {
  if (form.department_name) {
    const depts = await api.get('/admin/departments')
    const dep = depts.find(d => d.name === form.department_name)
    if (dep) {
      form.department_id = dep.id
      const res = await api.get(`/admin/departments`) // get doctors differently
      // fallback: show all doctors and filter by department name
    }
  }
})

async function submit() {
  if (!form.doctor_id) { ElMessage.warning('请选择医生'); return }
  if (!form.reg_date) { ElMessage.warning('请选择日期'); return }
  submitting.value = true
  try {
    const res = await api.post('/consultation/registration', {
      consultation_id: form.consultation_id,
      department_id: form.department_id,
      doctor_id: form.doctor_id,
      registration_date: form.reg_date.toISOString().split('T')[0],
      time_slot: form.time_slot,
    })
    ElMessage.success(res.message || '挂号成功')
    router.push('/registration/my')
  } finally {
    submitting.value = false
  }
}

function disabledDate(time) {
  return time.getTime() < Date.now() - 86400000
}
</script>

<style scoped>
.reg-page { max-width: 600px; margin: 20px auto; padding: 0 16px; }
</style>
