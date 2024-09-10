<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-7xl mx-auto">
      <!-- Empty state -->
      <div v-if="documents.length === 0 && !loading" class="text-center">
        <div class="bg-white rounded-lg shadow-xl p-8 max-w-2xl mx-auto">
          <svg
            class="mx-auto h-24 w-24 text-indigo-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h2 class="mt-6 text-3xl font-extrabold text-gray-900">No documents yet</h2>
          <p class="mt-2 text-lg text-gray-600">
            Get started by uploading your first document or importing text from a website.
          </p>
          <div class="mt-8">
            <DocumentUploadModal @document-loaded="handleDocumentLoaded">
              <template #default="{ openModal }">
                <button
                  @click="openModal"
                  class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  <svg
                    class="-ml-1 mr-3 h-5 w-5"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  Upload Your First Document
                </button>
              </template>
            </DocumentUploadModal>
          </div>
        </div>
      </div>
      <div v-else>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <div v-for="doc in documents" :key="doc.id" class="group">
            <router-link
              :to="`/uploads/${doc.id}/${doc.url_friendly_file_name}/read`"
              class="block"
            >
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
import { useRouter } from 'vue-router'
import axios from 'axios'
import DocumentUploadModal from '@/components/DocumentUploadModal.vue'

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
  components: {
    DocumentUploadModal
  },
  setup() {
    const documents = ref<Document[]>([])
    const loading = ref(false)
    const hasMore = ref(true)
    const nextCursor = ref<string | null>(null)
    const router = useRouter()

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
    const handleDocumentLoaded = (documentData: any) => {
      const documentUploadId = documentData.id || documentData.document_upload_id
      const newPath = `/uploads/${documentUploadId}/${documentData.url_friendly_file_name}/read`
      router.push(newPath)
    }

    const formatFileType = (fileType: string): string => {
      const fileTypeMap: { [key: string]: string } = {
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word',
        'application/pdf': 'PDF',
        'text/plain': 'Text',
        'text/markdown': 'Markdown',
        'application/json': 'JSON',
        'text/html': 'HTML',
        'application/epub+zip': 'EPUB',
        'text/csv': 'CSV'
      }

      // Check if we have a specific mapping for this file type
      if (fileType in fileTypeMap) {
        return fileTypeMap[fileType]
      }

      // If no specific mapping, fall back to the previous behavior
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
      formatFileType,
      handleDocumentLoaded
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
