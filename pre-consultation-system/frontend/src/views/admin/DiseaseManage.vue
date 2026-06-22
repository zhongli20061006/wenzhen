<template>
  <div class="admin-page">
    <el-container>
      <el-header>
        <div class="header-bar">
          <span><Collection style="margin-right:6px" />疾病管理</span>
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
          <el-button type="primary" @click="showDialog()"><Plus style="margin-right:4px" />新增疾病</el-button>
          <el-input v-model="searchText" placeholder="搜索疾病名称/ICD编码" clearable style="width:300px"><template #prefix><Search /></template></el-input>
        </div>
        <el-table :data="paginatedList" v-loading="loading" stripe>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="疾病名称" />
          <el-table-column prop="icd_code" label="ICD编码" width="100" />
          <el-table-column prop="urgency" label="紧急程度" width="80" />
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

        <el-dialog v-model="dialogVisible" :title="editingId ? '编辑疾病' : '新增疾病'" width="500px">
          <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
            <el-form-item label="疾病名称"><el-input v-model="form.name" /></el-form-item>
            <el-form-item label="ICD编码"><el-input v-model="form.icd_code" /></el-form-item>
            <el-form-item label="紧急程度">
              <el-select v-model="form.urgency" style="width:100%">
                <el-option label="紧急" value="紧急" />
                <el-option label="就诊" value="就诊" />
                <el-option label="观察" value="观察" />
              </el-select>
            </el-form-item>
            <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
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
const form = reactive({ name: '', icd_code: '', urgency: '就诊', description: '' })
const formRef = ref(null)
const rules = reactive({
  name: [{ required: true, message: '请输入疾病名称', trigger: 'blur' }]
})

const searchText = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

const filteredList = computed(() => {
  if (!searchText.value) return list.value
  const q = searchText.value.toLowerCase()
  return list.value.filter(item =>
    (item.name || '').toLowerCase().includes(q) ||
    (item.icd_code || '').toLowerCase().includes(q)
  )
})

const paginatedList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredList.value.slice(start, start + pageSize.value)
})

watch(searchText, () => { currentPage.value = 1 })

async function load() {
  loading.value = true
  try { list.value = await api.get('/admin/diseases') } finally { loading.value = false }
}

function showDialog(row) {
  if (row) {
    editingId.value = row.id
    Object.assign(form, { name: row.name, icd_code: row.icd_code || '', urgency: row.urgency, description: row.description || '' })
  } else {
    editingId.value = null
    Object.assign(form, { name: '', icd_code: '', urgency: '就诊', description: '' })
  }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    await formRef.value.validate().catch(() => { saving.value = false; throw new Error('validation') })
    if (editingId.value) {
      await api.put(`/admin/diseases/${editingId.value}`, form)
      ElMessage.success('更新成功')
    } else {
      await api.post('/admin/diseases', form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    load()
  } finally { saving.value = false }
}

async function handleDelete(id) {
  await ElMessageBox.confirm('确定删除？')
  await api.delete(`/admin/diseases/${id}`)
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
}
</style>
