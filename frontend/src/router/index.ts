import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import MainLayout from '@/components/MainLayout.vue'
import AuthView from '../views/AuthView.vue'
import EmailVerificationView from '@/views/EmailVerificationView.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/auth',
    name: 'auth',
    component: AuthView
  },
  {
    path: '/verify-email',
    name: 'verify-email',
    component: EmailVerificationView
  },
  {
    path: '/uploads/:documentId/:filename/read',
    name: 'FileView',
    component: MainLayout,
    props: (route) => ({ documentId: route.params.documentId })
  },
  {
    path: '/about',
    name: 'about',
    // route level code-splitting
    // this generates a separate chunk (About.[hash].js) for this route
    // which is lazy-loaded when the route is visited.
    component: () => import('../views/AboutView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router
