<template>
  <div class="profile-page">
    <el-container>
      <el-header>
        <div class="header-bar">
          <span><UserFilled style="margin-right:6px" />个人中心</span>
          <el-button @click="$router.push(getHomeRoute())"><HomeFilled style="margin-right:4px" />返回首页</el-button>
        </div>
      </el-header>
      <el-main>
        <el-card>
          <template #header><h3>账号信息</h3></template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="用户名">{{ profile.username }}</el-descriptions-item>
            <el-descriptions-item label="角色">
              <el-tag :type="roleType"><User style="margin-right:4px" />{{ roleLabel }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card v-if="profile.doctor" style="margin-top:16px">
          <template #header><h3>医生信息</h3></template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="姓名">{{ profile.doctor.name }}</el-descriptions-item>
            <el-descriptions-item label="职称">{{ profile.doctor.title }}</el-descriptions-item>
            <el-descriptions-item label="科室">{{ profile.doctor.department_name }}</el-descriptions-item>
            <el-descriptions-item label="简介">{{ profile.doctor.introduction || '无' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <div style="margin-top:16px;display:flex;gap:12px">
          <el-button v-if="isPatient" type="primary" @click="$router.push('/registration/my')">
            <List style="margin-right:4px" />我的挂号记录
          </el-button>
          <el-button v-if="isDoctor" type="primary" @click="$router.push('/doctor/today')">
            <User style="margin-right:4px" />今日患者
          </el-button>
          <el-button @click="logout"><SwitchButton style="margin-right:4px" />退出登录</el-button>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import api from '../api'

const router = useRouter()
const store = useUserStore()
const profile = ref({ username: '', role: '' })

const isPatient = computed(() => store.role === 'patient' || !store.role)
const isDoctor = computed(() => store.role === 'doctor')

const roleLabel = computed(() => {
  const map = { admin: '管理员', doctor: '医生', patient: '患者' }
  return map[profile.value.role] || profile.value.role
})

const roleType = computed(() => {
  const map = { admin: 'danger', doctor: 'warning', patient: 'info' }
  return map[profile.value.role] || 'info'
})

function getHomeRoute() {
  if (store.isAdmin) return '/admin/symptoms'
  if (store.isDoctor) return '/doctor/today'
  return '/consultation'
}

async function logout() {
  store.logout()
  router.push('/login')
}

onMounted(async () => {
  try {
    profile.value = await api.get('/auth/me')
  } catch {
    profile.value = { username: store.username, role: store.role }
  }
})
</script>

<style scoped>
.profile-page { max-width: 600px; margin: 0 auto; }
.header-bar { display: flex; justify-content: space-between; align-items: center; }

@media (max-width: 768px) {
  .profile-page { padding: 0 8px; }
  .header-bar { flex-wrap: wrap; gap: 8px; }
  .header-bar span { font-size: 16px; }
  .profile-page :deep(.el-descriptions__cell) { padding: 8px; font-size: 13px; }
  .profile-page :deep(.el-header) { height: auto !important; padding: 10px; }
  .profile-page :deep(.el-main) { padding: 12px; }
  .profile-page :deep(.el-card__body) { padding: 12px; }
  .profile-page div[style*="display:flex"] { flex-direction: column; gap: 8px !important; }
  .profile-page .el-button { min-height: 44px; }
}
</style>
