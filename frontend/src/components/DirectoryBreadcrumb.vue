<script setup lang="ts">
import { useDirectoryStore } from '@/store/directory'
import { computed } from 'vue'

const directoryStore = useDirectoryStore()

const breadcrumbs = computed(() => directoryStore.breadcrumbs)

const navigateTo = async (directoryId: string | null) => {
  // Only update URL, don't fetch content
  await directoryStore.navigateToDirectory(directoryId, { updateUrl: true, fetchContent: false })
}
</script>

<template>
  <nav class="flex py-3 px-5 text-gray-700 rounded-lg bg-white shadow-sm" aria-label="Breadcrumb">
    <ol class="inline-flex items-center space-x-1 md:space-x-3 flex-wrap">
      <li v-for="(crumb, index) in breadcrumbs" :key="index" class="inline-flex items-center">
        <div v-if="index === 0" class="inline-flex items-center">
          <button
            @click="navigateTo(crumb._id)"
            class="inline-flex items-center text-sm font-medium text-indigo-600 hover:text-indigo-800"
          >
            <svg
              class="w-4 h-4 mr-2"
              fill="currentColor"
              viewBox="0 0 20 20"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"
              ></path>
            </svg>
            {{ crumb.name }}
          </button>
        </div>
        <div v-else class="flex items-center">
          <svg
            class="w-6 h-6 text-gray-400"
            fill="currentColor"
            viewBox="0 0 20 20"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              fill-rule="evenodd"
              d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
              clip-rule="evenodd"
            ></path>
          </svg>
          <button
            @click="navigateTo(crumb._id)"
            class="ml-1 text-sm font-medium text-indigo-600 hover:text-indigo-800 md:ml-2"
            :class="{ 'font-semibold': index === breadcrumbs.length - 1 }"
          >
            {{ crumb.name }}
          </button>
        </div>
      </li>
    </ol>
  </nav>
</template>

<style scoped>
.breadcrumb-enter-active,
.breadcrumb-leave-active {
  transition:
    opacity 0.3s,
    transform 0.3s;
}
.breadcrumb-enter-from,
.breadcrumb-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>
