<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import DirectoryTree from './DirectoryTree.vue'
import { useDirectoryStore } from '@/store/directory'

const directoryStore = useDirectoryStore()
const router = useRouter()

// Default to collapsed on mobile, expanded on desktop
const isSidebarOpen = ref(window.innerWidth > 768)

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}

onMounted(async () => {
  // Only fetch directories and navigate if we're on the home page
  if (router.currentRoute.value.name === 'home') {
    // Fetch all directories first
    await directoryStore.fetchAllDirectories()

    // Navigate to the root directory
    await directoryStore.navigateToDirectory(null)
  }
})

const navigateToHome = () => {
  router.push('/')
}

const navigateToSettings = () => {
  router.push('/settings')
}
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

      <!-- Navigation -->
      <div class="p-2 border-b border-gray-100">
        <div class="space-y-1">
          <button
            @click="navigateToHome"
            class="flex items-center w-full p-2 rounded-md hover:bg-indigo-50 text-gray-700 hover:text-indigo-600 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"
              />
            </svg>
            <span v-if="isSidebarOpen" class="ml-3 text-sm">Home</span>
          </button>

          <button
            @click="navigateToSettings"
            class="flex items-center w-full p-2 rounded-md hover:bg-indigo-50 text-gray-700 hover:text-indigo-600 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
                clip-rule="evenodd"
              />
            </svg>
            <span v-if="isSidebarOpen" class="ml-3 text-sm">Settings</span>
          </button>
        </div>
      </div>

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
