<template>
  <div class="admin-page">
    <el-container>
      <el-header>
        <div class="header-bar">
          <span>症状管理</span>
          <el-menu mode="horizontal" :ellipsis="false" router>
            <el-menu-item index="/admin/symptoms">症状</el-menu-item>
            <el-menu-item index="/admin/diseases">疾病</el-menu-item>
            <el-menu-item index="/admin/rules">规则</el-menu-item>
            <el-menu-item index="/admin/statistics">统计</el-menu-item>
          </el-menu>
          <div>
            <el-button text @click="$router.push('/profile')">个人中心</el-button>
            <el-button text @click="logout">退出</el-button>
          </div>
        </div>
      </el-header>
      <el-main>
        <el-button type="primary" @click="showDialog()" style="margin-bottom:12px">新增症状</el-button>
        <el-table :data="list" v-loading="loading" stripe>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="标准名称" />
          <el-table-column prop="aliases" label="别名" />
          <el-table-column prop="category" label="分类" />
          <el-table-column prop="level" label="级别" width="80" />
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button size="small" @click="showDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="dialogVisible" :title="editingId ? '编辑症状' : '新增症状'" width="500px">
          <el-form :model="form" label-width="80px">
            <el-form-item label="名称">
              <el-input v-model="form.name" />
            </el-form-item>
            <el-form-item label="别名">
              <el-input v-model="form.aliases" placeholder="逗号分隔" />
            </el-form-item>
            <el-form-item label="分类">
              <el-select v-model="form.category" style="width:100%">
                <el-option v-for="c in ['全身','呼吸系统','消化系统','循环系统','神经','运动系统','皮肤','五官','口腔','头颈部']" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
            <el-form-item label="级别">
              <el-radio-group v-model="form.level">
                <el-radio value="主要">主要</el-radio>
                <el-radio value="次要">次要</el-radio>
              </el-radio-group>
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

const form = reactive({ name: '', aliases: '', category: '', level: '次要' })

async function load() {
  loading.value = true
  try { list.value = await api.get('/admin/symptoms') } finally { loading.value = false }
}

function showDialog(row) {
  if (row) {
    editingId.value = row.id
    Object.assign(form, { name: row.name, aliases: row.aliases || '', category: row.category || '', level: row.level })
  } else {
    editingId.value = null
    Object.assign(form, { name: '', aliases: '', category: '', level: '次要' })
  }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editingId.value) {
      await api.put(`/admin/symptoms/${editingId.value}`, form)
      ElMessage.success('更新成功')
    } else {
      await api.post('/admin/symptoms', form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    load()
  } finally { saving.value = false }
}

async function handleDelete(id) {
  await ElMessageBox.confirm('确定删除？')
  await api.delete(`/admin/symptoms/${id}`)
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
