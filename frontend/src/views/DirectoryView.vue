<script setup lang="ts">
import { useDirectoryStore } from '@/store/directory'
import { onMounted, computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DirectoryBreadcrumb from '@/components/DirectoryBreadcrumb.vue'
import DocumentUploadModal from '@/components/DocumentUploadModal.vue'
import { useToast } from 'vue-toastification'

const directoryStore = useDirectoryStore()
const route = useRoute()
const router = useRouter()
const toast = useToast()

const isLoading = computed(() => directoryStore.isLoading)
const currentDirectory = computed(() => directoryStore.currentDirectory)
const directoryContents = computed(() => directoryStore.directoryContents)

// Modal states
const showCreateDirModal = ref(false)
const showRenameDirModal = ref(false)
const showDeleteDirModal = ref(false)
const newDirName = ref('')
const selectedDirId = ref('')
const recursiveDelete = ref(false)

// Document drag state
const draggedDocumentId = ref<string | null>(null)
const draggedDirectoryId = ref<string | null>(null)
const dropTargetId = ref<string | null>(null)

// Load directory contents based on route params
const loadDirectoryContents = async () => {
  try {
    const path = (route.params.path as string) || ''
    if (path) {
      await directoryStore.navigateToPath(path)
    } else {
      await directoryStore.navigateToDirectory(null)
    }
  } catch (error: any) {
    toast.error(error.message || 'Failed to load directory')
    router.push({ name: 'directory', params: { path: '' } })
  }
}

// Watch for route changes
watch(
  () => route.params.path,
  () => {
    loadDirectoryContents()
  }
)

// Create directory
const createDirectory = async () => {
  if (newDirName.value.trim()) {
    try {
      const parentId = currentDirectory.value?._id || null
      await directoryStore.createDirectory(newDirName.value, parentId)
      showCreateDirModal.value = false
      newDirName.value = ''
      toast.success('Directory created successfully')
    } catch (error: any) {
      toast.error(error.message || 'Failed to create directory')
    }
  }
}

// Rename directory
const openRenameModal = (dirId: string, name: string) => {
  selectedDirId.value = dirId
  newDirName.value = name
  showRenameDirModal.value = true
}

const renameDirectory = async () => {
  if (newDirName.value.trim() && selectedDirId.value) {
    try {
      await directoryStore.updateDirectory(selectedDirId.value, newDirName.value)
      showRenameDirModal.value = false
      newDirName.value = ''
      selectedDirId.value = ''
      toast.success('Directory renamed successfully')
    } catch (error: any) {
      toast.error(error.message || 'Failed to rename directory')
    }
  }
}

// Delete directory
const openDeleteModal = (dirId: string) => {
  selectedDirId.value = dirId
  recursiveDelete.value = false
  showDeleteDirModal.value = true
}

const deleteDirectory = async () => {
  if (selectedDirId.value) {
    try {
      await directoryStore.deleteDirectory(selectedDirId.value, recursiveDelete.value)
      showDeleteDirModal.value = false
      selectedDirId.value = ''
      toast.success('Directory deleted successfully')
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete directory')
    }
  }
}

// Navigate to directory
const navigateToDirectory = (dirId: string) => {
  const directory = directoryStore.getDirectoryById(dirId)
  if (directory) {
    const path = directory.path.substring(1) // Remove leading slash
    router.push({ name: 'directory', params: { path } })
  }
}

// Navigate to document
const navigateToDocument = (documentId: string, filename: string) => {
  router.push({
    name: 'FileView',
    params: { documentId, filename }
  })
}

// Drag and drop handlers
const onDragStart = (event: DragEvent, type: 'document' | 'directory', id: string) => {
  if (type === 'document') {
    draggedDocumentId.value = id
    draggedDirectoryId.value = null
  } else {
    draggedDirectoryId.value = id
    draggedDocumentId.value = null
  }

  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', id)
  }
}

const onDragOver = (event: DragEvent, id: string | null) => {
  event.preventDefault()
  dropTargetId.value = id

  // Don't allow dropping a directory into itself or its children
  if (draggedDirectoryId.value) {
    const draggedDir = directoryStore.getDirectoryById(draggedDirectoryId.value)
    const targetDir = id ? directoryStore.getDirectoryById(id) : null

    if (draggedDir && targetDir) {
      // Check if target is a child of dragged directory
      if (targetDir.path.startsWith(draggedDir.path + '/')) {
        event.dataTransfer!.dropEffect = 'none'
        return
      }

      // Check if target is the same as dragged directory
      if (draggedDir._id === targetDir._id) {
        event.dataTransfer!.dropEffect = 'none'
        return
      }
    }
  }

  event.dataTransfer!.dropEffect = 'move'
}

const onDragLeave = () => {
  dropTargetId.value = null
}

const onDrop = async (event: DragEvent, targetDirId: string | null) => {
  event.preventDefault()
  dropTargetId.value = null

  if (draggedDocumentId.value) {
    try {
      await directoryStore.moveDocument(draggedDocumentId.value, targetDirId)
      toast.success('Document moved successfully')
    } catch (error: any) {
      toast.error(error.message || 'Failed to move document')
    }
  } else if (draggedDirectoryId.value) {
    try {
      await directoryStore.moveDirectory(draggedDirectoryId.value, targetDirId)
      toast.success('Directory moved successfully')
    } catch (error: any) {
      toast.error(error.message || 'Failed to move directory')
    }
  }

  draggedDocumentId.value = null
  draggedDirectoryId.value = null
}

// Add the handleDocumentLoaded function
const handleDocumentLoaded = (documentData: any) => {
  const documentId = documentData.id || documentData.document_upload_id
  const newPath = `/uploads/${documentId}/${documentData.url_friendly_file_name}/read`
  router.push(newPath)
}

onMounted(() => {
  directoryStore.fetchAllDirectories()
  loadDirectoryContents()
})
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <DirectoryBreadcrumb class="mb-6" />

    <div class="mb-6 flex justify-between items-center">
      <h1 class="text-2xl font-bold text-gray-800">
        {{ currentDirectory ? currentDirectory.name : 'Home' }}
      </h1>
      <button
        @click="showCreateDirModal = true"
        class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors flex items-center"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5 mr-2"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
            clip-rule="evenodd"
          />
        </svg>
        New Directory
      </button>
    </div>

    <div v-if="isLoading" class="flex justify-center items-center py-12">
      <div
        class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"
      ></div>
    </div>

    <div v-else-if="directoryContents">
      <!-- Directories -->
      <div class="mb-8">
        <h2 class="text-lg font-semibold text-gray-700 mb-4">Directories</h2>

        <div
          class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
          @dragover.prevent="onDragOver($event, null)"
          @dragleave="onDragLeave"
          @drop="onDrop($event, null)"
        >
          <div
            v-for="directory in directoryContents.directories"
            :key="directory._id"
            class="bg-white rounded-lg shadow-sm p-4 border border-gray-200 hover:shadow-md transition-shadow cursor-pointer flex flex-col"
            :class="{ 'border-indigo-500 border-2': dropTargetId === directory._id }"
            draggable="true"
            @dragstart="onDragStart($event, 'directory', directory._id)"
            @dragover.stop.prevent="onDragOver($event, directory._id)"
            @dragleave.stop="onDragLeave"
            @drop.stop="onDrop($event, directory._id)"
          >
            <div class="flex items-center mb-2" @click="navigateToDirectory(directory._id)">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-8 w-8 text-indigo-500 mr-3"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
              </svg>
              <span class="text-gray-800 font-medium truncate flex-grow">{{ directory.name }}</span>
            </div>

            <div class="flex justify-end mt-auto pt-2 space-x-2">
              <button
                @click.stop="openRenameModal(directory._id, directory.name)"
                class="text-gray-500 hover:text-indigo-600"
                title="Rename"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-5 w-5"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"
                  />
                </svg>
              </button>
              <button
                @click.stop="openDeleteModal(directory._id)"
                class="text-gray-500 hover:text-red-600"
                title="Delete"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-5 w-5"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fill-rule="evenodd"
                    d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                    clip-rule="evenodd"
                  />
                </svg>
              </button>
            </div>
          </div>

          <div
            v-if="directoryContents.directories.length === 0"
            class="col-span-full text-center py-8 text-gray-500"
          >
            <div class="flex flex-col items-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-12 w-12 text-gray-400 mb-4"
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
              <p class="mb-4">No directories found</p>
              <button
                @click="showCreateDirModal = true"
                class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
              >
                Create Your First Directory
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Documents -->
      <div>
        <h2 class="text-lg font-semibold text-gray-700 mb-4">Documents</h2>

        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          <div
            v-for="document in directoryContents.documents"
            :key="document._id"
            class="bg-white rounded-lg shadow-sm p-4 border border-gray-200 hover:shadow-md transition-shadow cursor-pointer"
            draggable="true"
            @dragstart="onDragStart($event, 'document', document._id)"
            @click="navigateToDocument(document._id, document.file_details.file_name)"
          >
            <div class="flex items-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-8 w-8 text-blue-500 mr-3"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
                  clip-rule="evenodd"
                />
              </svg>
              <div class="flex-grow">
                <div class="text-gray-800 font-medium truncate">
                  {{ document.custom_title || document.file_details.file_name }}
                </div>
                <div class="text-gray-500 text-sm">
                  {{ document.file_details.file_type.toUpperCase() }}
                </div>
              </div>
            </div>
          </div>

          <div
            v-if="directoryContents.documents.length === 0"
            class="col-span-full text-center py-8 text-gray-500"
          >
            <div class="flex flex-col items-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-12 w-12 text-gray-400 mb-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p class="mb-4">No documents found in this directory</p>
              <DocumentUploadModal @document-loaded="handleDocumentLoaded">
                <template #default="{ openModal }">
                  <button
                    @click="openModal"
                    class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
                  >
                    Upload a Document
                  </button>
                </template>
              </DocumentUploadModal>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-12 text-gray-500">
      <div class="flex flex-col items-center">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-16 w-16 text-gray-400 mb-4"
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
        <h2 class="text-2xl font-bold text-gray-700 mb-2">Welcome to Directories</h2>
        <p class="mb-6 text-lg">Organize your documents into folders for better management</p>
        <button
          @click="showCreateDirModal = true"
          class="px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
        >
          Create Your First Directory
        </button>
      </div>
    </div>

    <!-- Create Directory Modal -->
    <div
      v-if="showCreateDirModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-white rounded-lg p-6 w-96 shadow-xl">
        <h3 class="text-lg font-semibold mb-4">Create New Directory</h3>
        <div class="mb-4">
          <label class="block text-gray-700 text-sm font-medium mb-2" for="dirName">
            Directory Name
          </label>
          <input
            id="dirName"
            v-model="newDirName"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Enter directory name"
            @keyup.enter="createDirectory"
          />
        </div>
        <div class="flex justify-end space-x-3">
          <button
            @click="showCreateDirModal = false"
            class="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 focus:outline-none"
          >
            Cancel
          </button>
          <button
            @click="createDirectory"
            class="px-4 py-2 text-white bg-indigo-600 rounded-md hover:bg-indigo-700 focus:outline-none"
            :disabled="!newDirName.trim()"
          >
            Create
          </button>
        </div>
      </div>
    </div>

    <!-- Rename Directory Modal -->
    <div
      v-if="showRenameDirModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-white rounded-lg p-6 w-96 shadow-xl">
        <h3 class="text-lg font-semibold mb-4">Rename Directory</h3>
        <div class="mb-4">
          <label class="block text-gray-700 text-sm font-medium mb-2" for="renameDirName">
            New Name
          </label>
          <input
            id="renameDirName"
            v-model="newDirName"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Enter new name"
            @keyup.enter="renameDirectory"
          />
        </div>
        <div class="flex justify-end space-x-3">
          <button
            @click="showRenameDirModal = false"
            class="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 focus:outline-none"
          >
            Cancel
          </button>
          <button
            @click="renameDirectory"
            class="px-4 py-2 text-white bg-indigo-600 rounded-md hover:bg-indigo-700 focus:outline-none"
            :disabled="!newDirName.trim()"
          >
            Rename
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Directory Modal -->
    <div
      v-if="showDeleteDirModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    >
      <div class="bg-white rounded-lg p-6 w-96 shadow-xl">
        <h3 class="text-lg font-semibold mb-4">Delete Directory</h3>
        <p class="text-gray-700 mb-4">Are you sure you want to delete this directory?</p>
        <div class="mb-4">
          <label class="flex items-center">
            <input
              v-model="recursiveDelete"
              type="checkbox"
              class="form-checkbox h-5 w-5 text-indigo-600"
            />
            <span class="ml-2 text-gray-700"
              >Delete all subdirectories and move documents to root</span
            >
          </label>
        </div>
        <div class="flex justify-end space-x-3">
          <button
            @click="showDeleteDirModal = false"
            class="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 focus:outline-none"
          >
            Cancel
          </button>
          <button
            @click="deleteDirectory"
            class="px-4 py-2 text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.directory-item {
  transition: all 0.2s ease;
}
</style>
