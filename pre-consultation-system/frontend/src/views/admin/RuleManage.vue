<template>
  <div class="admin-page">
    <el-container>
      <el-header>
        <div class="header-bar">
          <span><SetUp style="margin-right:6px" />鉴别规则管理</span>
          <el-menu mode="horizontal" :ellipsis="false" router>
            <el-menu-item index="/admin/symptoms"><Memo />症状</el-menu-item>
            <el-menu-item index="/admin/diseases"><Collection />疾病</el-menu-item>
            <el-menu-item index="/admin/rules"><SetUp />规则</el-menu-item>
            <el-menu-item index="/admin/statistics"><DataLine />统计</el-menu-item>
          </el-menu>
          <el-button text @click="logout"><SwitchButton />退出</el-button>
        </div>
      </el-header>
      <el-main>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <el-button type="primary" @click="showDialog()"><Plus style="margin-right:4px" />新增规则</el-button>
          <el-input v-model="searchText" placeholder="搜索规则名称" clearable style="width:300px"><template #prefix><Search /></template></el-input>
        </div>
        <el-table :data="paginatedList" v-loading="loading" stripe>
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

        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="filteredList.length"
          layout="total, prev, pager, next"
          style="margin-top:12px;justify-content:flex-end"
          small
          background
        />

        <el-dialog v-model="dialogVisible" :title="editingId ? '编辑规则' : '新增规则'" width="600px">
          <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
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
import { ref, reactive, computed, watch, onMounted } from 'vue'
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
const formRef = ref(null)
const rules = reactive({
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }]
})

const searchText = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

const filteredList = computed(() => {
  if (!searchText.value) return list.value
  const q = searchText.value.toLowerCase()
  return list.value.filter(item =>
    (item.name || '').toLowerCase().includes(q)
  )
})

const paginatedList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredList.value.slice(start, start + pageSize.value)
})

watch(searchText, () => { currentPage.value = 1 })

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
    await formRef.value.validate().catch(() => { saving.value = false; throw new Error('validation') })
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

@media (max-width: 768px) {
  .admin-page { max-width: 100%; }
  .admin-page :deep(.el-header) { height: auto !important; padding: 8px; }
  .header-bar { flex-wrap: wrap; gap: 6px; }
  .header-bar > span { font-size: 16px; width: 100%; }
  .header-bar .el-menu { width: 100%; overflow-x: auto; }
  .header-bar .el-menu .el-menu-item { padding: 0 10px; font-size: 13px; }
  .admin-page :deep(.el-main) { padding: 8px; }
  .admin-page div[style*="display:flex"][style*="justify-content"] { flex-direction: column; gap: 8px; align-items: stretch !important; }
  .admin-page div[style*="display:flex"][style*="justify-content"] .el-input { width: 100% !important; }
  .admin-page div[style*="display:flex"][style*="justify-content"] .el-button { width: 100%; }
  .admin-page :deep(.el-table) { font-size: 13px; }
  .admin-page :deep(.el-table__body-wrapper) { overflow-x: auto; }
  .admin-page :deep(.el-table .el-table__cell) { white-space: nowrap; }
  .admin-page :deep(.el-dialog) { width: 95% !important; max-width: 95%; }
  .admin-page :deep(.el-dialog__body) { padding: 12px; }
  .admin-page :deep(.el-form-item) { flex-wrap: wrap; }
  .admin-page :deep(.el-form-item__label) { float: none; display: block; text-align: left; padding-bottom: 4px; }
  .admin-page :deep(.el-form-item__content) { margin-left: 0 !important; width: 100%; }
  .admin-page :deep(.el-pagination) { flex-wrap: wrap; justify-content: center !important; }
  .admin-page :deep(.el-input-number) { width: 100% !important; }
  .admin-page :deep(.el-row) { flex-direction: column; }
  .admin-page :deep(.el-col) { width: 100% !important; max-width: 100%; }
}
</style>
