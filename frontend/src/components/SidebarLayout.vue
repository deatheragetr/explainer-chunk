<script setup lang="ts">
import { ref, onMounted } from 'vue'
import DirectoryTree from './DirectoryTree.vue'
import { useDirectoryStore } from '@/store/directory'

const directoryStore = useDirectoryStore()

// Default to collapsed on mobile, expanded on desktop
const isSidebarOpen = ref(window.innerWidth > 768)

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}

// This is the key fix - make the sidebar initialization a one-time operation
// that doesn't respond to route changes or re-trigger navigation
onMounted(async () => {
  // Only fetch directories on the first mount - don't navigate yet
  await directoryStore.fetchAllDirectories()

  // Don't automatically navigate in the sidebar - let the route handlers do it
  // This prevents the sidebar from overriding URL-based navigation
  console.log('Sidebar mounted - directories loaded')
})
</script>

<template>
  <div class="flex">
    <!-- Sidebar -->
    <div
      :class="[
        'bg-white shadow-sm transition-all duration-300 ease-in-out flex flex-col fixed left-0 top-20 bottom-0 z-10',
        isSidebarOpen ? 'w-64' : 'w-12'
      ]"
    >
      <!-- Toggle button -->
      <button
        @click="toggleSidebar"
        class="absolute -right-3 top-4 bg-white rounded-full p-1 shadow-md text-gray-500 hover:text-indigo-600 focus:outline-none z-20"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            v-if="isSidebarOpen"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 19l-7-7 7-7"
          />
          <path
            v-else
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 5l7 7-7 7"
          />
        </svg>
      </button>

      <!-- Directory Tree -->
      <div class="flex-grow overflow-auto p-2">
        <DirectoryTree :collapsed="!isSidebarOpen" />
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-grow" :class="{ 'ml-64': isSidebarOpen, 'ml-12': !isSidebarOpen }">
      <slot></slot>
    </div>
  </div>
</template>
