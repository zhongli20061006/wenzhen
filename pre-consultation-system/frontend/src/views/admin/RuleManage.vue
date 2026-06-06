<template>
  <div class="admin-page">
    <el-container>
      <el-header>
        <div class="header-bar">
          <span>鉴别规则管理</span>
          <el-menu mode="horizontal" :ellipsis="false" router>
            <el-menu-item index="/admin/symptoms">症状</el-menu-item>
            <el-menu-item index="/admin/diseases">疾病</el-menu-item>
            <el-menu-item index="/admin/rules">规则</el-menu-item>
            <el-menu-item index="/admin/statistics">统计</el-menu-item>
          </el-menu>
          <el-button text @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main>
        <el-button type="primary" @click="showDialog()" style="margin-bottom:12px">新增规则</el-button>
        <el-table :data="list" v-loading="loading" stripe>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="规则名称" width="200" />
          <el-table-column label="触发条件" width="200">
            <template #default="{ row }">{{ JSON.stringify(row.condition_json) }}</template>
          </el-table-column>
          <el-table-column label="调整结果" width="200">
            <template #default="{ row }">{{ JSON.stringify(row.result_json) }}</template>
          </el-table-column>
          <el-table-column prop="priority" label="优先级" width="80" />
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button size="small" @click="showDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="dialogVisible" :title="editingId ? '编辑规则' : '新增规则'" width="600px">
          <el-form :model="form" label-width="100px">
            <el-form-item label="规则名称"><el-input v-model="form.name" /></el-form-item>
            <el-form-item label="触发症状">
              <el-input v-model="form.condition_symptoms" placeholder="逗号分隔，如：发热,咳嗽" />
            </el-form-item>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="发病天数<">
                  <el-input-number v-model="form.condition_days_lt" :min="0" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="严重程度>=">
                  <el-input-number v-model="form.condition_severity_gte" :min="0" :max="10" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="疾病调整">
              <div v-for="(adj, idx) in adjustments" :key="idx" style="display:flex;gap:8px;margin-bottom:8px">
                <el-input v-model="adj.disease" placeholder="疾病名称" style="width:200px" />
                <el-input-number v-model="adj.score" :step="0.1" :min="-0.5" :max="0.5" style="width:140px" />
                <el-button @click="adjustments.splice(idx, 1)" v-if="adjustments.length > 1">×</el-button>
              </div>
              <el-button size="small" @click="adjustments.push({ disease: '', score: 0 })">+ 添加调整</el-button>
            </el-form-item>
            <el-form-item label="优先级">
              <el-input-number v-model="form.priority" :min="1" :max="100" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
          </template>
        </el-dialog>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

const router = useRouter()
const store = useUserStore()
const list = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)

const form = reactive({
  name: '',
  condition_symptoms: '',
  condition_days_lt: null,
  condition_severity_gte: null,
  priority: 1,
})
const adjustments = reactive([{ disease: '', score: 0 }])

async function load() {
  loading.value = true
  try { list.value = await api.get('/admin/differential-rules') } finally { loading.value = false }
}

function showDialog(row) {
  if (row) {
    editingId.value = row.id
    const cond = row.condition_json
    form.name = row.name
    form.condition_symptoms = (cond.symptoms || []).join(',')
    form.condition_days_lt = cond.onset_days_lt ?? null
    form.condition_severity_gte = cond.severity_gte ?? null
    form.priority = row.priority
    const adj = row.result_json.disease_adjust || {}
    adjustments.length = 0
    Object.entries(adj).forEach(([d, s]) => { adjustments.push({ disease: d, score: s }) })
    if (adjustments.length === 0) adjustments.push({ disease: '', score: 0 })
  } else {
    editingId.value = null
    form.name = ''
    form.condition_symptoms = ''
    form.condition_days_lt = null
    form.condition_severity_gte = null
    form.priority = 1
    adjustments.length = 0
    adjustments.push({ disease: '', score: 0 })
  }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const condition = { symptoms: form.condition_symptoms.split(/[,，]/).map(s => s.trim()).filter(Boolean) }
    if (form.condition_days_lt !== null) condition.onset_days_lt = form.condition_days_lt
    if (form.condition_severity_gte !== null) condition.severity_gte = form.condition_severity_gte
    const adj = {}
    adjustments.forEach(a => { if (a.disease && a.score) adj[a.disease] = a.score })
    const body = { name: form.name, condition_json: condition, result_json: { disease_adjust: adj }, priority: form.priority }
    if (editingId.value) {
      await api.put(`/admin/differential-rules/${editingId.value}`, body)
      ElMessage.success('更新成功')
    } else {
      await api.post('/admin/differential-rules', body)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    load()
  } finally { saving.value = false }
}

async function handleDelete(id) {
  await ElMessageBox.confirm('确定删除？')
  await api.delete(`/admin/differential-rules/${id}`)
  ElMessage.success('删除成功')
  load()
}

function logout() { store.logout(); router.push('/login') }

onMounted(load)
</script>

<style scoped>
.admin-page { max-width: 1000px; margin: 0 auto; }
.header-bar { display: flex; justify-content: space-between; align-items: center; }
</style>
