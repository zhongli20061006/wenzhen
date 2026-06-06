<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2>智能预问诊系统</h2>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin" :loading="loading" style="width:100%">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="hint">测试账号：admin/admin123、doctor1/doctor123、patient1/patient123</div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const store = useUserStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({ username: 'patient1', password: 'patient123' })
const rules = {
  username: [{ required: true, message: '请输入用户名' }],
  password: [{ required: true, message: '请输入密码' }],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await store.login(form.username, form.password)
    ElMessage.success('登录成功')
    if (store.isAdmin) router.push('/admin/symptoms')
    else if (store.isDoctor) router.push('/doctor/today')
    else router.push('/consultation')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.login-card { width: 420px; }
.login-card h2 { text-align: center; margin-bottom: 24px; color: #409eff; }
.hint { font-size: 12px; color: #999; text-align: center; margin-top: 12px; }
</style>
