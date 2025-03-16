import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import MainLayout from '@/components/MainLayout.vue'
import AuthView from '../views/AuthView.vue'
import EmailVerificationView from '@/views/EmailVerificationView.vue'
import UserSettingsView from '@/views/UserSettingsView.vue'
import { useDirectoryStore } from '@/store/directory'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'home',
    meta: { requiresAuth: true },
    component: HomeView
  },
  {
    path: '/directories/:path(.*)/:id',
    name: 'directory',
    meta: { requiresAuth: true },
    component: HomeView,
    props: true
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
    meta: { requiresAuth: true },
    component: MainLayout,
    props: (route) => ({ documentId: route.params.documentId })
  },
  {
    path: '/settings',
    name: 'settings',
    component: UserSettingsView,
    meta: { requiresAuth: true }
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

router.beforeEach(async (to, from, next) => {
  // Auth checks (keep your existing code here)

  // Add special handling for directory routes
  if (to.name === 'home' || to.name === 'directory') {
    const directoryStore = useDirectoryStore()

    // Pre-fetch directories if not already loaded
    if (directoryStore.directories.length === 0) {
      await directoryStore.fetchAllDirectories()
    }

    // Clear directory initialization flag when changing routes
    directoryStore.routeInitialized = false

    // For 'directory' routes, extract path and ID
    if (to.name === 'directory') {
      const path = to.params.path as string
      const id = to.params.id as string

      // Wait for route initialization to complete
      await directoryStore.initializeFromRoute(path, id)
    } else if (to.name === 'home') {
      // Explicitly initialize from root path
      await directoryStore.initializeFromRoute('/')
    }
  }

  next()
})

router.afterEach((to, from) => {
  const directoryStore = useDirectoryStore()

  console.log(`Route changed: ${from.fullPath} -> ${to.fullPath}`)

  // Always handle directory navigation through routes
  if (to.name === 'home') {
    // Mark that we're now at root
    console.log('Navigated to home route - ensuring current directory is null')
    directoryStore.currentDirectory = null
    directoryStore.breadcrumbs = [{ _id: null, name: 'Home', path: '/' }]
  }
})

export default router
