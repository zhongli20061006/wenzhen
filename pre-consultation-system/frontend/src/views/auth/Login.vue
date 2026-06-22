<template>
  <div class="login-page">
    <div class="login-backdrop"></div>
    <el-card class="login-card">
      <div class="login-card-accent"></div>
      <div class="login-header">
        <h1 class="login-title">智能预问诊系统</h1>
        <p class="login-subtitle">AI 驱动的症状分析与科室推荐</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="login-form">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名">
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码">
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin" :loading="loading" class="login-btn">
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>
      <p class="login-footer">v1.0</p>
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

const form = reactive({ username: '', password: '' })
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
/* ─── Page Layout ─── */
.login-page {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #0F1B3D 0%, #1A3A6B 40%, #1E6FFF 100%);
  overflow: hidden;
}

/* ─── Background Pattern Overlay ─── */
.login-backdrop {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 25% 30%, rgba(255,255,255,0.04) 0%, transparent 50%),
    radial-gradient(circle at 75% 70%, rgba(30,111,255,0.08) 0%, transparent 40%),
    radial-gradient(circle at 50% 50%, rgba(255,255,255,0.015) 1px, transparent 1px);
  background-size: 100% 100%, 100% 100%, 32px 32px;
  pointer-events: none;
}

/* ─── Card ─── */
.login-card {
  position: relative;
  width: 100%;
  max-width: 440px;
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--radius-lg, 16px);
  box-shadow:
    0 20px 60px rgba(30,111,255,0.15),
    0 4px 16px rgba(0,0,0,0.06);
  animation: fadeInUp 0.5s ease-out;
  border: 1px solid rgba(255,255,255,0.2);
}

.login-card :deep(.el-card__body) {
  padding: 40px;
}

.login-card-accent {
  position: absolute;
  top: 0;
  left: 40px;
  right: 40px;
  height: 4px;
  background: linear-gradient(90deg, #1E6FFF, #4D94FF);
  border-radius: 0 0 4px 4px;
}

/* ─── Header ─── */
.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-title {
  font-size: 26px;
  font-weight: 700;
  color: #1E293B;
  margin: 0 0 8px;
  letter-spacing: 1px;
}

.login-subtitle {
  font-size: 14px;
  color: #94A3B8;
  margin: 0;
  letter-spacing: 0.3px;
}

/* ─── Form ─── */
.login-form {
  width: 100%;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 24px;
}

.login-form :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 500;
  color: #64748B;
  letter-spacing: 0.5px;
  padding-bottom: 6px;
}

.login-form :deep(.el-input__wrapper) {
  height: 44px;
  border-radius: 8px;
  border: 1px solid #E2E8F0;
  box-shadow: none !important;
  padding-left: 12px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.login-form :deep(.el-input__wrapper:hover) {
  border-color: #94A3B8;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--color-primary, #1E6FFF);
  box-shadow: 0 0 0 3px rgba(30,111,255,0.1) !important;
}

.login-form :deep(.el-input__inner) {
  height: 44px;
  font-size: 14px;
  color: #1E293B;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: #CBD5E1;
}

.login-form :deep(.el-input__prefix) {
  margin-right: 8px;
}

.login-form :deep(.el-input__prefix-inner) {
  color: #94A3B8;
  font-size: 16px;
}

.login-form :deep(.el-input__wrapper.is-focus) .el-input__prefix-inner {
  color: var(--color-primary, #1E6FFF);
}

/* ─── Button ─── */
.login-btn {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #1E6FFF, #4D94FF);
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  color: #fff;
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: pointer;
}

.login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(30,111,255,0.35);
  background: linear-gradient(135deg, #1E6FFF, #4D94FF);
}

.login-btn:active {
  transform: translateY(0);
}

.login-btn:focus {
  background: linear-gradient(135deg, #1E6FFF, #4D94FF);
}

/* ─── Footer ─── */
.login-footer {
  text-align: center;
  font-size: 11px;
  color: #CBD5E1;
  margin: 24px 0 0;
  letter-spacing: 0.5px;
}

/* ─── Animation ─── */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ─── Responsive ─── */
@media (max-width: 768px) {
  .login-page {
    padding: 0 20px;
  }
  .login-card {
    max-width: 100%;
  }
  .login-card :deep(.el-card__body) {
    padding: 32px 24px;
  }
  .login-title {
    font-size: 22px;
  }
  .login-subtitle {
    font-size: 13px;
  }
}

@media (max-width: 480px) {
  .login-page {
    padding: 0 12px;
  }
  .login-card {
    border-radius: 12px;
  }
  .login-card :deep(.el-card__body) {
    padding: 24px 16px;
  }
  .login-title {
    font-size: 20px;
  }
  .login-subtitle {
    font-size: 12px;
  }
  .login-form :deep(.el-form-item) {
    margin-bottom: 20px;
  }
  .login-btn {
    height: 44px;
    font-size: 15px;
  }
}
</style>
