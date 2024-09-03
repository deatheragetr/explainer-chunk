<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-7xl mx-auto">
      <h1 class="text-4xl font-extrabold text-center text-indigo-800 mb-12">Your Documents</h1>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        <div v-for="doc in documents" :key="doc.id" class="group">
          <router-link :to="`/uploads/${doc.id}/${doc.url_friendly_file_name}/read`" class="block">
            <div
              class="bg-white rounded-lg shadow-lg overflow-hidden transform transition duration-300 ease-in-out group-hover:scale-105"
            >
              <div class="thumbnail-container">
                <img
                  v-if="doc.thumbnail && doc.thumbnail.presigned_url"
                  :src="doc.thumbnail.presigned_url"
                  :alt="doc.file_name"
                  class="w-full h-full object-cover"
                />
                <div
                  v-else
                  class="w-full h-full flex items-center justify-center bg-gradient-to-br from-blue-100 to-indigo-200"
                >
                  <svg
                    class="w-2/5 h-2/5 text-indigo-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    ></path>
                  </svg>
                </div>
              </div>
              <div class="p-4">
                <h2 class="text-lg font-semibold text-gray-800 truncate">{{ doc.file_name }}</h2>
                <p class="text-sm text-gray-600 mt-1">{{ formatFileType(doc.file_type) }}</p>
              </div>
            </div>
          </router-link>
        </div>
      </div>

      <div v-if="loading" class="flex justify-center mt-8">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
      </div>

      <div v-if="hasMore" class="flex justify-center mt-8">
        <button
          @click="loadMore"
          class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-full shadow-md transition duration-300 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-opacity-50"
        >
          Load More
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
// The script section remains unchanged
import { defineComponent, ref, onMounted } from 'vue'
import axios from 'axios'

interface Document {
  id: string
  file_name: string
  file_type: string
  url_friendly_file_name: string
  thumbnail?: {
    presigned_url: string
  }
}

export default defineComponent({
  name: 'HomeView',
  setup() {
    const documents = ref<Document[]>([])
    const loading = ref(false)
    const hasMore = ref(true)
    const nextCursor = ref<string | null>(null)

    const fetchDocuments = async () => {
      if (loading.value) return

      loading.value = true
      try {
        const response = await axios.get('http://localhost:8000/document-uploads', {
          params: {
            before: nextCursor.value,
            limit: 12
          }
        })

        documents.value.push(...response.data.documents)
        nextCursor.value = response.data.next_cursor
        hasMore.value = !!response.data.next_cursor
      } catch (error) {
        console.error('Error fetching documents:', error)
      } finally {
        loading.value = false
      }
    }

    const loadMore = () => {
      fetchDocuments()
    }

    const formatFileType = (fileType: string) => {
      return fileType.split('/').pop()?.toUpperCase() || fileType
    }

    onMounted(() => {
      fetchDocuments()
    })

    return {
      documents,
      loading,
      hasMore,
      loadMore,
      formatFileType
    }
  }
})
</script>

<style scoped>
.thumbnail-container {
  width: 100%;
  padding-top: 100%; /* This creates a 1:1 aspect ratio */
  position: relative;
  overflow: hidden;
}

.thumbnail-container > img,
.thumbnail-container > div {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}
</style>
