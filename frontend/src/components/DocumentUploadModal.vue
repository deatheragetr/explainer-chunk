<template>
  <div>
    <button
      @click="openModal"
      class="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-3 rounded-lg font-bold text-lg transition duration-300 ease-in-out transform hover:from-purple-700 hover:to-indigo-700 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 shadow-lg"
    >
      Upload or Import Text
    </button>

    <TransitionRoot appear :show="isOpen" as="template">
      <CustomDialog as="div" @close="closeModal" class="relative z-10">
        <TransitionChild
          as="template"
          enter="duration-300 ease-out"
          enter-from="opacity-0"
          enter-to="opacity-100"
          leave="duration-200 ease-in"
          leave-from="opacity-100"
          leave-to="opacity-0"
        >
          <div class="fixed inset-0 bg-black bg-opacity-25" />
        </TransitionChild>

        <div class="fixed inset-0 overflow-y-auto">
          <div class="flex min-h-full items-center justify-center p-4 text-center">
            <TransitionChild
              as="template"
              enter="duration-300 ease-out"
              enter-from="opacity-0 scale-95"
              enter-to="opacity-100 scale-100"
              leave="duration-200 ease-in"
              leave-from="opacity-100 scale-100"
              leave-to="opacity-0 scale-95"
            >
              <DialogPanel
                class="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all"
              >
                <DialogTitle as="h3" class="text-lg font-medium leading-6 text-gray-900 mb-4">
                  Add Website or Document
                </DialogTitle>

                <!-- Add directory selection dropdown before the upload buttons -->
                <div class="mb-4">
                  <label
                    for="directory-select"
                    class="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Save to Folder
                  </label>
                  <select
                    id="directory-select"
                    v-model="selectedDirectoryId"
                    class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                  >
                    <option :value="null">Root (No Folder)</option>
                    <option v-for="dir in directories" :key="dir._id" :value="dir._id">
                      {{ dir.name }}
                    </option>
                  </select>
                </div>

                <!-- URL Input -->
                <div class="mb-4">
                  <label for="url-input" class="block text-sm font-medium text-gray-700 mb-2"
                    >Website URL</label
                  >
                  <input
                    id="url-input"
                    v-model="url"
                    @keyup.enter="loadContent"
                    class="w-full p-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Enter website URL"
                  />
                </div>

                <!-- File Drop Zone -->
                <div
                  @dragover.prevent
                  @drop.prevent="onFileDrop"
                  @click="triggerFileInput"
                  class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-indigo-500 transition-colors duration-300"
                >
                  <input
                    type="file"
                    @change="handleFileUpload"
                    accept="application/pdf, application/epub+zip, application/json, text/markdown, text/plain, .md, .markdown, .txt, .json, .pdf, .docx, .csv, .xlsx"
                    class="hidden"
                    ref="fileInput"
                  />
                  <div class="text-gray-600">
                    <svg
                      class="mx-auto h-12 w-12 text-gray-400"
                      stroke="currentColor"
                      fill="none"
                      viewBox="0 0 48 48"
                      aria-hidden="true"
                    >
                      <path
                        d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                    </svg>
                    <p class="mt-1">Drag and drop a file here, or click to select a file</p>
                  </div>
                </div>

                <!-- File name display -->
                <p v-if="fileName" class="mt-2 text-sm text-gray-600">
                  Selected file: {{ fileName }}
                </p>

                <p v-if="error" class="text-red-500 mt-2">{{ error }}</p>

                <!-- Import Progress Bar -->
                <div v-if="importProgress" class="mt-4">
                  <div class="text-sm font-medium text-gray-700">
                    Processing Document: {{ importProgress.progress || 0 }}%
                    {{ importProgress.status }}
                  </div>
                  <div class="mt-1 h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                    <div
                      class="h-full bg-indigo-600 transition-all duration-500 ease-in-out"
                      :style="{ width: `${importProgress.progress || 0}%` }"
                    ></div>
                  </div>
                </div>

                <div class="mt-4 flex justify-end">
                  <button
                    type="button"
                    class="inline-flex justify-center rounded-md border border-transparent bg-indigo-100 px-4 py-2 text-sm font-medium text-indigo-900 hover:bg-indigo-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
                    @click="loadContent"
                    :disabled="isLoading"
                  >
                    {{ isLoading ? 'Loading...' : 'Load Content' }}
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </CustomDialog>
    </TransitionRoot>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed } from 'vue'

import {
  Dialog as CustomDialog,
  DialogPanel,
  DialogTitle,
  TransitionChild,
  TransitionRoot
} from '@headlessui/vue'
import { uploadLargeFile } from '@/utils/fileUpload'
import api from '@/api/axios'
import { UnsupportedFileTypeError } from '@/utils/textExtract'
import { useDirectoryStore } from '@/store/directory'

interface ImportProgress {
  status: string
  progress: number | null
  payload: {
    presigned_url?: string
    file_type?: string
    document_upload_id?: string
    url_friendly_file_name?: string
  }
}

interface ImportDocumentUploadResponse {
  id: string
}

interface WebsiteCaptureResponse {
  url: string
  document_upload_id: string
}

interface UploadResponse {
  id: string
  file_name: string
  file_type: string
  url_friendly_file_name: string
}

export default defineComponent({
  name: 'DocumentUploadModal',
  components: {
    CustomDialog,
    DialogPanel,
    DialogTitle,
    TransitionChild,
    TransitionRoot
  },
  emits: ['document-loaded'],
  setup(props, { emit }) {
    const isOpen = ref(false)
    const url = ref('')
    const error = ref('')
    const importProgress = ref<ImportProgress | null>(null)
    const isLoading = ref(false)
    const fileInput = ref<HTMLInputElement | null>(null)
    const fileName = ref('')
    const websocket = ref<WebSocket | null>(null)
    const directoryStore = useDirectoryStore()
    const selectedDirectoryId = ref<string | null>(null)

    const directories = computed(() => {
      return directoryStore.directories || []
    })

    const currentDirectory = computed(() => {
      return directoryStore.currentDirectory
    })

    const openModal = () => {
      isOpen.value = true
      directoryStore.fetchAllDirectories()
      selectedDirectoryId.value = currentDirectory.value?._id || null
    }

    const closeModal = () => {
      isOpen.value = false
      resetState()
    }

    const triggerFileInput = () => {
      fileInput.value?.click()
    }

    const resetState = () => {
      url.value = ''
      error.value = ''
      importProgress.value = null
      isLoading.value = false
      fileName.value = ''
    }

    const handleFileUpload = (event: Event) => {
      const file = (event.target as HTMLInputElement).files?.[0]
      if (file) {
        fileName.value = file.name
        uploadFile(file)
      }
    }

    const onFileDrop = (event: DragEvent) => {
      const file = event.dataTransfer?.files[0]
      if (file) {
        fileName.value = file.name
        uploadFile(file)
      }
    }

    const getFileType = (file: File) => {
      let fileType = ''
      if (file) {
        // The basic idea here is to be flexible with file inputs, a defer first to the file type and then then the extension
        let fileSupported: Boolean = false
        if (file.type) {
          fileSupported = true
          switch (file.type) {
            case 'application/pdf':
              break
            case 'application/epub+zip':
              break
            case 'application/json':
              break
            case 'text/markdown':
            case 'text/plain': // This will catch .txt files
              break
            case 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
              break
            case 'text/csv':
            case 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
              break
            default:
              fileSupported = false
          }
          if (fileSupported) {
            fileType = file.type
          }
        }
        // If MIME TYPE unsupported or not defined, fallback to using the file extension
        if (!fileSupported) {
          const extension = file.name.split('.').pop()?.toLowerCase()
          switch (extension) {
            case 'pdf':
              fileType = 'application/pdf'
              break
            case 'json':
              fileType = 'application/json'
              break
            // case 'xml':
            case 'epub':
              fileType = 'application/epub+zip'
              break
            case 'csv':
            case 'xlsx':
              fileType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
              break
            case 'md':
            case 'markdown':
              fileType = 'text/markdown'
              break
            case 'txt': // Explicitly handle .txt files as Markdown
              fileType = 'text/plain'
              break
            case 'docx':
              fileType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
              break
            // ... handle other file types ...
            default:
              throw new UnsupportedFileTypeError(`Unsupported file type ${extension}/${file.type}`)
          }
        }
      }
      return fileType
    }

    const uploadFile = async (file: File) => {
      isLoading.value = true
      error.value = ''
      importProgress.value = { status: 'Uploading', progress: 0, payload: {} }
      const fileType = getFileType(file)

      try {
        // Create a FormData object for the API call
        const formData = new FormData()
        formData.append('file', file)

        // Add directory_id if selected
        if (selectedDirectoryId.value) {
          formData.append('directory_id', selectedDirectoryId.value)
        }

        // Use the standard concurrency parameter (4 is the default)
        const response = await uploadLargeFile(file, fileType, importProgress)

        // After upload is complete, update the document with the directory if needed
        if (selectedDirectoryId.value && response && response.id) {
          try {
            await api.patch(`/document-uploads/${response.id}`, {
              directory_id: selectedDirectoryId.value
            })
          } catch (dirError) {
            console.error('Error setting directory:', dirError)
          }
        }

        importProgress.value = { status: 'Complete', progress: 100, payload: response }
        const emitBody = { ...response, file: file }
        emit('document-loaded', emitBody)
        closeModal()
      } catch (e) {
        error.value = `Error uploading file: ${e instanceof Error ? e.message : String(e)}`
      } finally {
        isLoading.value = false
      }
    }

    const loadContent = async () => {
      if (!url.value && !fileName.value) {
        error.value = 'Please enter a URL or select a file'
        return
      }

      if (url.value) {
        try {
          isLoading.value = true
          error.value = ''
          importProgress.value = { status: 'Capturing website', progress: 0, payload: {} }
          const importDocRes = await api.post<ImportDocumentUploadResponse>(
            '/document-uploads/imports',
            {}
          )
          connectWebSocket(importDocRes.data.id)

          const captureRes = await api.post<WebsiteCaptureResponse>('/capture-website/', {
            url: url.value,
            document_upload_id: importDocRes.data.id
          })

          importProgress.value = { status: 'Complete', progress: 100, payload: captureRes.data }
          // emit('document-loaded', captureRes.data) // TODO: Confirm we even need this?
          // closeModal()
        } catch (e) {
          console.error('Error capturing website:', e)
          error.value = 'Failed to capture website. Please try again.'
        } finally {
          isLoading.value = false
        }
      }
    }

    const connectWebSocket = (connectionId: string) => {
      websocket.value = new WebSocket(`ws://localhost:8000/ws/document-upload/${connectionId}`)

      websocket.value.onopen = () => {
        console.log('WebSocket connected')
      }

      websocket.value.onmessage = (event) => {
        const data: ImportProgress = JSON.parse(event.data)
        console.log('WebSocket message:', data)
        importProgress.value = data
        console.log('capture status: ', importProgress.value)
        if (data.status === 'COMPLETE' && data.payload.presigned_url) {
          emit('document-loaded', data.payload)

          closeModal()
          if (websocket.value) {
            websocket.value.close()
          }
        }
      }

      websocket.value.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      websocket.value.onclose = () => {
        console.log('WebSocket disconnected')
      }
    }

    return {
      isOpen,
      url,
      error,
      importProgress,
      isLoading,
      fileInput,
      fileName,
      openModal,
      closeModal,
      handleFileUpload,
      onFileDrop,
      loadContent,
      triggerFileInput,
      selectedDirectoryId,
      directories
    }
  }
})
</script>
