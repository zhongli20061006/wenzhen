<template>
  <div class="admin-page">
    <el-container>
      <el-header>
        <div class="header-bar">
          <span>疾病管理</span>
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
        <el-button type="primary" @click="showDialog()" style="margin-bottom:12px">新增疾病</el-button>
        <el-table :data="list" v-loading="loading" stripe>
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

        <el-dialog v-model="dialogVisible" :title="editingId ? '编辑疾病' : '新增疾病'" width="500px">
          <el-form :model="form" label-width="100px">
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
const form = reactive({ name: '', icd_code: '', urgency: '就诊', description: '' })

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
