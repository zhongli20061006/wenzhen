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
          <el-select v-model="form.doctor_id" placeholder="请选择医生" @change="onDoctorChange" style="width:100%" :loading="loadingDoctors">
            <el-option v-for="d in doctors" :key="d.id" :label="`${d.name} ${d.title||''}`" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="就诊日期">
          <el-date-picker v-model="form.reg_date" type="date" :disabled-date="disabledDate" @change="onDateChange" style="width:100%" />
        </el-form-item>
        <el-form-item label="就诊时段" v-loading="loadingSlots">
          <el-radio-group v-model="form.time_slot" style="display:flex;flex-wrap:wrap;gap:8px">
            <el-radio v-for="s in timeslots" :key="s.value" :value="s.value" border :disabled="s.remaining <= 0">
              {{ s.value }}
              <span :class="s.remaining <= 2 ? 'low' : ''">剩余{{ s.remaining }}号</span>
            </el-radio>
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
const loadingSlots = ref(false)
const submitting = ref(false)

const form = reactive({
  consultation_id: route.query.consultation_id || store.sessionId,
  department_id: Number(route.query.department_id) || null,
  doctor_id: null,
  reg_date: new Date(),
  time_slot: '',
})

onMounted(async () => {
  try {
    departments.value = await api.get('/consultation/departments')
    if (form.department_id) {
      await loadDoctors(form.department_id)
    }
  } finally {
    loadingDepts.value = false
  }
})

async function onDeptChange(deptId) {
  form.doctor_id = null
  timeslots.value = []
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

async function onDoctorChange() {
  timeslots.value = []
  await loadAvailableSlots()
}

async function onDateChange() {
  await loadAvailableSlots()
}

async function loadAvailableSlots() {
  if (!form.doctor_id) return
  const d = form.reg_date
  if (!d) return
  loadingSlots.value = true
  try {
    const dateStr = d.toISOString().split('T')[0]
    timeslots.value = await api.get('/consultation/timeslots/available', {
      params: { doctor_id: form.doctor_id, registration_date: dateStr },
    })
    const first = timeslots.value.find(t => t.remaining > 0)
    if (first) form.time_slot = first.value
  } finally {
    loadingSlots.value = false
  }
}

async function submit() {
  if (!form.doctor_id) { ElMessage.warning('请选择医生'); return }
  if (!form.department_id) { ElMessage.warning('请选择科室'); return }
  if (!form.reg_date) { ElMessage.warning('请选择日期'); return }
  if (!form.time_slot) { ElMessage.warning('请选择时段'); return }
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
.low { color: #e6a23c; font-size: 12px; }
</style>
