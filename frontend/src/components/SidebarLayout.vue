<!-- src/components/SidebarLayout.vue -->
<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import DirectoryTree from './DirectoryTree.vue'
import OutlineTree from './OutlineTree.vue'
import { useDirectoryStore } from '@/store/directory'
import { useDocumentStore } from '@/store/document'

const directoryStore = useDirectoryStore()
const documentStore = useDocumentStore()
const route = useRoute()

// Default to collapsed on mobile, expanded on desktop
const isSidebarOpen = ref(window.innerWidth > 768)

// Tabs state (only used when on document view)
const activeTab = ref('outline') // Default to outline when on document page

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}

// Determine whether we're on a document view
const isDocumentView = computed(() => {
  return route.path.includes('/uploads/') && route.path.includes('/read')
})

// Extract document ID from route if we're on a document view
const documentId = computed(() => {
  if (isDocumentView.value && route.params.documentId) {
    return route.params.documentId.toString()
  }
  return null
})

// Watch for changes in the document ID and load document details
watch(
  documentId,
  async (newDocumentId, oldDocumentId) => {
    if (newDocumentId && newDocumentId !== oldDocumentId) {
      await documentStore.fetchDocumentDetails(newDocumentId)
      if (documentStore.outline && documentStore.outline.length > 0) {
        activeTab.value = 'outline'
      } else {
        activeTab.value = 'directories'
      }
    } else if (!newDocumentId) {
      documentStore.clearDocumentData()
    }
  },
  { immediate: true }
)

onMounted(async () => {
  // Only fetch directories on the first mount - don't navigate yet
  await directoryStore.fetchAllDirectories()
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

      <!-- Tabs (only show if in document view and sidebar is open) -->
      <div v-if="isDocumentView && isSidebarOpen" class="flex border-b border-gray-200 mt-2 px-2">
        <button
          @click="activeTab = 'outline'"
          :class="[
            'px-3 py-2 text-sm font-medium rounded-t-md -mb-px',
            activeTab === 'outline'
              ? 'bg-white text-indigo-600 border-t border-l border-r border-gray-200'
              : 'text-gray-500 hover:text-gray-700'
          ]"
        >
          Outline
        </button>
        <button
          @click="activeTab = 'directories'"
          :class="[
            'px-3 py-2 text-sm font-medium rounded-t-md -mb-px',
            activeTab === 'directories'
              ? 'bg-white text-indigo-600 border-t border-l border-r border-gray-200'
              : 'text-gray-500 hover:text-gray-700'
          ]"
        >
          Folders
        </button>
      </div>

      <!-- Icons-only tabs (if in document view and sidebar is collapsed) -->
      <div
        v-if="isDocumentView && !isSidebarOpen"
        class="flex flex-col items-center mt-2 space-y-4"
      >
        <button
          @click="activeTab = 'outline'"
          :class="[
            'p-1 rounded',
            activeTab === 'outline'
              ? 'bg-indigo-100 text-indigo-600'
              : 'text-gray-500 hover:text-gray-700'
          ]"
          title="Document Outline"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
        </button>
        <button
          @click="activeTab = 'directories'"
          :class="[
            'p-1 rounded',
            activeTab === 'directories'
              ? 'bg-indigo-100 text-indigo-600'
              : 'text-gray-500 hover:text-gray-700'
          ]"
          title="Folders"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
            />
          </svg>
        </button>
      </div>

      <!-- Main content area -->
      <div class="flex-grow overflow-auto p-2 mt-2">
        <!-- Document view: Show either outline or directories based on active tab -->
        <template v-if="isDocumentView">
          <OutlineTree v-if="activeTab === 'outline'" :collapsed="!isSidebarOpen" />
          <DirectoryTree v-else :collapsed="!isSidebarOpen" />
        </template>

        <!-- Non-document view: Just show directories -->
        <template v-else>
          <DirectoryTree :collapsed="!isSidebarOpen" />
        </template>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-grow" :class="{ 'ml-64': isSidebarOpen, 'ml-12': !isSidebarOpen }">
      <slot></slot>
    </div>
  </div>
</template>
