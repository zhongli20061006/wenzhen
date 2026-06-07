<template>
  <div class="reg-page">
    <div class="nav-bar">
      <el-button text @click="$router.back()">返回</el-button>
      <el-button text @click="$router.push({ name: 'Profile' })">个人中心</el-button>
    </div>
    <el-card>
      <template #header><h2>挂号确认</h2></template>
      <el-form :model="form" label-width="100px" v-loading="loadingDepts">
        <el-form-item label="科室">
          <el-select v-model="form.department_id" placeholder="请选择科室" @change="onDeptChange" style="width:100%" :loading="loadingDepts">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="医生">
          <el-select v-model="form.doctor_id" placeholder="请选择医生" style="width:100%" :loading="loadingDoctors">
            <el-option v-for="d in doctors" :key="d.id" :label="`${d.name} ${d.title||''}`" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="就诊日期">
          <el-date-picker v-model="form.reg_date" type="date" :disabled-date="disabledDate" style="width:100%" />
        </el-form-item>
        <el-form-item label="就诊时段">
          <el-radio-group v-model="form.time_slot" style="display:flex;flex-wrap:wrap;gap:8px">
            <el-radio v-for="s in timeslots" :key="s.value" :value="s.value" border>{{ s.value }}</el-radio>
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
const departments = ref([])
const doctors = ref([])
const timeslots = ref([])
const loadingDepts = ref(true)
const loadingDoctors = ref(false)
const submitting = ref(false)

const form = reactive({
  consultation_id: route.query.consultation_id || store.sessionId,
  department_id: Number(route.query.department_id) || null,
  doctor_id: null,
  reg_date: new Date(),
  time_slot: '08:30',
})

onMounted(async () => {
  try {
    const [depts, slots] = await Promise.all([
      api.get('/consultation/departments'),
      api.get('/consultation/timeslots'),
    ])
    departments.value = depts
    timeslots.value = slots
    if (form.time_slot === '08:30' && slots.length) {
      form.time_slot = slots[0].value
    }
    if (form.department_id) {
      await loadDoctors(form.department_id)
    }
  } finally {
    loadingDepts.value = false
  }
})

async function onDeptChange(deptId) {
  form.doctor_id = null
  if (deptId) {
    await loadDoctors(deptId)
  } else {
    doctors.value = []
  }
}

async function loadDoctors(deptId) {
  loadingDoctors.value = true
  try {
    doctors.value = await api.get('/consultation/doctors', { params: { department_id: deptId } })
  } finally {
    loadingDoctors.value = false
  }
}

async function submit() {
  if (!form.doctor_id) { ElMessage.warning('请选择医生'); return }
  if (!form.department_id) { ElMessage.warning('请选择科室'); return }
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
    router.push({ name: 'MyRegistrations' })
  } finally {
    submitting.value = false
  }
}

function disabledDate(time) {
  return time.getTime() < Date.now() - 86400000
}
</script>

<style scoped>
.reg-page { max-width: 600px; margin: 10px auto; padding: 0 16px; }
.nav-bar { display: flex; justify-content: space-between; margin-bottom: 8px; }
</style>
