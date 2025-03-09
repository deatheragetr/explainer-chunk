<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'
import NavBar from '@/components/NavBar.vue'
import SidebarLayout from '@/components/SidebarLayout.vue'
import { computed, watch } from 'vue'
import { useDocumentTitle } from '@/composables/useDocumentTitle'

const route = useRoute()
const { resetDocument } = useDocumentTitle()

const showNavBar = computed(() => {
  // Add routes where you don't want to show the navbar
  const routesWithoutNavBar = ['/auth']
  return !routesWithoutNavBar.includes(route.path)
})

const useSidebar = computed(() => {
  // Add routes where you want to use the sidebar layout
  const routesWithSidebar = ['/', '/settings']
  return routesWithSidebar.some((path) => route.path.startsWith(path))
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
