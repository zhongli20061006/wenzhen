import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  { path: '/', redirect: '/consultation' },
  { path: '/login', name: 'Login', component: () => import('../views/auth/Login.vue') },

  { path: '/consultation', name: 'Consultation', component: () => import('../views/patient/Consultation.vue') },
  { path: '/consultation/:id/result', name: 'Result', component: () => import('../views/patient/Result.vue') },
  { path: '/registration/confirm', name: 'RegistrationConfirm', component: () => import('../views/patient/RegistrationConfirm.vue') },
  { path: '/registration/my', name: 'MyRegistrations', component: () => import('../views/patient/MyRegistrations.vue') },

  { path: '/doctor/today', name: 'TodayPatients', component: () => import('../views/doctor/TodayPatients.vue'), meta: { role: 'doctor' } },
  { path: '/doctor/patient/:id', name: 'PatientReport', component: () => import('../views/doctor/PatientReport.vue'), meta: { role: 'doctor' } },

  { path: '/admin/symptoms', name: 'SymptomManage', component: () => import('../views/admin/SymptomManage.vue'), meta: { role: 'admin' } },
  { path: '/admin/diseases', name: 'DiseaseManage', component: () => import('../views/admin/DiseaseManage.vue'), meta: { role: 'admin' } },
  { path: '/admin/rules', name: 'RuleManage', component: () => import('../views/admin/RuleManage.vue'), meta: { role: 'admin' } },
  { path: '/admin/statistics', name: 'Statistics', component: () => import('../views/admin/Statistics.vue'), meta: { role: 'admin' } },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const store = useUserStore()
  if (to.meta.role && store.role !== to.meta.role) {
    next('/login')
  } else {
    next()
  }
})

export default router
