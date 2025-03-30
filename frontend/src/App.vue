// src/App.vue
<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'
import NavBar from '@/components/NavBar.vue'
import SidebarLayout from '@/components/SidebarLayout.vue'
import { computed, watch, onMounted } from 'vue'
import { useDocumentTitle } from '@/composables/useDocumentTitle'
import store from '@/store/auth'

const route = useRoute()
const { resetDocument } = useDocumentTitle()

const showNavBar = computed(() => {
  // Don't show navbar on auth pages
  return !route.path.startsWith('/auth')
})

const useSidebar = computed(() => {
  // Only show sidebar on the home page and document pages
  // Explicitly exclude settings and auth pages
  if (route.path === '/settings' || route.path.startsWith('/auth')) {
    return false
  }

  // Only show sidebar on home, directory, and document pages
  return (
    route.path === '/' || route.path.includes('/uploads/') || route.path.includes('/directories/')
  )
})

// Watch for route changes to reset document title when not on a document page
watch(
  () => route.path,
  (newPath) => {
    // If not on a document upload view, reset the document title
    if (!newPath.includes('/uploads/') || !newPath.includes('/read')) {
      resetDocument()
    }
  }
)

// Perform initial authentication check when app loads
onMounted(async () => {
  await store.dispatch('checkAuth')
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-indigo-50 to-blue-100">
    <NavBar v-if="showNavBar" />

    <div :class="{ 'pt-20': showNavBar }">
      <template v-if="useSidebar">
        <SidebarLayout>
          <RouterView :key="route.fullPath" />
        </SidebarLayout>
      </template>
      <template v-else>
        <RouterView :key="route.fullPath" />
      </template>
    </div>
  </div>
</template>
