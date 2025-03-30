// src/router/index.ts
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import MainLayout from '@/components/MainLayout.vue'
import AuthView from '../views/AuthView.vue'
import EmailVerificationView from '@/views/EmailVerificationView.vue'
import UserSettingsView from '@/views/UserSettingsView.vue'
import { useDirectoryStore } from '@/store/directory'
import store from '@/store/auth'

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

// Global navigation guard to check authentication
router.beforeEach(async (to, from, next) => {
  console.log('Navigation guard checking auth for route:', to.fullPath)

  // Check if the route requires authentication
  if (to.matched.some((record) => record.meta.requiresAuth)) {
    // If not logged in or token is not available, redirect to auth page
    if (!store.getters.isAuthenticated) {
      console.log('Not authenticated, attempting token refresh')
      // Try to refresh the token once before redirecting
      try {
        await store.dispatch('refreshToken')
        // If successful, continue to the requested route
        console.log('Token refresh successful, continuing to:', to.fullPath)
        next()
      } catch (error) {
        console.log('Authentication failed, redirecting to login page')

        // Save the original path for redirect (avoiding nested redirects)
        const destinationPath = to.fullPath.split('?redirect=')[0]

        // Don't add redirect params if we're already heading to an auth page
        if (!destinationPath.includes('/auth')) {
          console.log('Redirecting to auth with redirect param:', destinationPath)
          next({
            path: '/auth',
            query: { redirect: destinationPath }
          })
        } else {
          console.log('Redirecting to auth without redirect param')
          next({ path: '/auth' })
        }
      }
    } else {
      // User is authenticated, proceed
      console.log('User is authenticated, proceeding to:', to.fullPath)
      next()
    }
  } else {
    // Route doesn't require authentication, proceed
    console.log('Route does not require auth, proceeding to:', to.fullPath)
    next()
  }
})

router.beforeEach(async (to, from, next) => {
  // In router, fetch content but don't update URL
  if (to.name === 'directory' && to.params.id) {
    const directoryStore = useDirectoryStore()
    await directoryStore.navigateToDirectory(to.params.id, { updateUrl: false, fetchContent: true })
  } else if (to.name === 'home') {
    const directoryStore = useDirectoryStore()
    await directoryStore.navigateToDirectory(null, { updateUrl: false, fetchContent: true })
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
