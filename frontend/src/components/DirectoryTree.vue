<script setup lang="ts">
import { useDirectoryStore } from '@/store/directory'
import { computed, ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import type { DirectoryTreeNode, LightweightDocument } from '@/types/directory'

const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false
  }
})

const directoryStore = useDirectoryStore()
const router = useRouter()

const directoryTree = computed(() => directoryStore.directoryTree)
const currentDirectoryId = computed(() => directoryStore.getCurrentDirectoryId)
const directoryContents = computed(() => directoryStore.directoryContents)

// Track documents for each directory
const directoryDocuments = ref<Map<string | null, LightweightDocument[]>>(new Map())

// Update directoryDocuments when directoryContents changes
watch(
  directoryContents,
  (contents) => {
    if (contents && currentDirectoryId.value !== undefined) {
      // Store documents for the current directory
      directoryDocuments.value.set(currentDirectoryId.value, contents.documents || [])
    }
  },
  { immediate: true }
)

// Fetch directory contents when navigating to a directory
const fetchDirectoryContents = async (directoryId: string | null) => {
  try {
    await directoryStore.fetchDirectoryContents(directoryId)
    // Get the contents from the store after fetching
    const contents = directoryStore.directoryContents
    if (contents && contents.documents) {
      directoryDocuments.value.set(directoryId, contents.documents)
    }
  } catch (error) {
    console.error('Error fetching directory contents:', error)
  }
}

// Prefetch contents for all directories in the tree
const prefetchDirectoryContents = async () => {
  // First fetch root contents
  await fetchDirectoryContents(null)

  // Then fetch for all directories in the tree
  const fetchForNode = async (node: DirectoryTreeNode) => {
    await fetchDirectoryContents(node._id)
    for (const child of node.children) {
      await fetchForNode(child)
    }
  }

  for (const node of directoryTree.value) {
    await fetchForNode(node)
  }
}

// Call prefetch on component mount
onMounted(async () => {
  await prefetchDirectoryContents()
})

const toggleExpand = async (node: DirectoryTreeNode, event: Event) => {
  event.stopPropagation()

  // Toggle the expanded state
  node.isExpanded = !node.isExpanded

  // If expanding the node, fetch its contents if not already loaded
  if (node.isExpanded && !directoryDocuments.value.has(node._id)) {
    await fetchDirectoryContents(node._id)
  }
}

const navigateToDirectory = async (directoryId: string) => {
  const directory = directoryStore.getDirectoryById(directoryId)
  if (directory) {
    await router.push('/')
    await directoryStore.navigateToDirectory(directoryId)
  }
}

const navigateToRoot = async () => {
  await router.push('/')
  await directoryStore.navigateToDirectory(null)
}

const navigateToDocument = (document: LightweightDocument) => {
  // @ts-ignore - We know these properties exist based on the interface
  router.push(`/uploads/${document.id}/${document.url_friendly_file_name}/read`)
}

const getFileIcon = (fileType: string) => {
  // Return appropriate icon based on file type
  if (fileType.includes('pdf')) {
    return 'pdf'
  } else if (fileType.includes('word') || fileType.includes('docx')) {
    return 'word'
  } else if (
    fileType.includes('excel') ||
    fileType.includes('spreadsheet') ||
    fileType.includes('csv')
  ) {
    return 'excel'
  } else if (fileType.includes('html')) {
    return 'html'
  } else if (fileType.includes('markdown') || fileType.includes('md')) {
    return 'markdown'
  } else if (fileType.includes('json')) {
    return 'json'
  } else if (fileType.includes('text') || fileType.includes('txt')) {
    return 'text'
  } else {
    return 'generic'
  }
}

const showCreateModal = ref(false)
const newDirectoryName = ref('')
const parentDirectoryId = ref<string | null>(null)

const openCreateModal = (parentId: string | null = null, event: Event) => {
  event.stopPropagation()
  parentDirectoryId.value = parentId
  newDirectoryName.value = ''
  showCreateModal.value = true
}

const createDirectory = async () => {
  if (newDirectoryName.value.trim()) {
    try {
      await directoryStore.createDirectory(newDirectoryName.value, parentDirectoryId.value)
      showCreateModal.value = false
      newDirectoryName.value = ''
    } catch (error) {
      console.error('Failed to create directory:', error)
    }
  }
}
</script>

<template>
  <div class="directory-tree">
    <div v-if="!collapsed" class="flex justify-between items-center mb-3">
      <h3 class="text-sm font-semibold text-gray-700">Directories</h3>
      <button
        @click="openCreateModal(null, $event)"
        class="text-indigo-600 hover:text-indigo-800 focus:outline-none"
        title="Add root directory"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
            clip-rule="evenodd"
          />
        </svg>
      </button>
    </div>

    <div class="mb-2">
      <div
        class="flex items-center py-2 px-2 rounded-md cursor-pointer hover:bg-indigo-50 transition-colors"
        :class="{ 'bg-indigo-100': currentDirectoryId === null, 'justify-center': collapsed }"
        @click="() => {}"
        @dblclick="navigateToRoot"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5 text-indigo-600"
          :class="{ 'mr-2': !collapsed }"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"
          />
        </svg>
        <span v-if="!collapsed" class="text-gray-700 text-sm">Home</span>
      </div>

      <!-- Root level documents -->
      <div v-if="!collapsed" class="ml-5 mt-1">
        <div
          v-for="doc in directoryDocuments.get(null) || []"
          :key="doc.id"
          class="flex items-center py-2 px-2 rounded-md cursor-pointer hover:bg-indigo-50 transition-colors"
          @dblclick="navigateToDocument(doc)"
        >
          <!-- File type icon -->
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5 mr-2 text-blue-500"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
              clip-rule="evenodd"
            />
          </svg>
          <span class="text-gray-700 text-sm truncate">{{ doc.title }}</span>
        </div>
      </div>
    </div>

    <div class="directory-nodes">
      <template v-for="node in directoryTree" :key="node._id">
        <div class="directory-node">
          <!-- Directory header -->
          <div
            class="flex items-center py-2 px-2 rounded-md cursor-pointer hover:bg-indigo-50 transition-colors group"
            :class="{
              'bg-indigo-100': currentDirectoryId === node._id,
              'justify-center': collapsed
            }"
            @click="toggleExpand(node, $event)"
            @dblclick="navigateToDirectory(node._id)"
          >
            <button
              v-if="
                !collapsed &&
                (node.children.length > 0 || (directoryDocuments.get(node._id)?.length ?? 0) > 0)
              "
              @click.stop="toggleExpand(node, $event)"
              class="mr-1 text-gray-500 focus:outline-none"
            >
              <svg
                v-if="!node.isExpanded"
                xmlns="http://www.w3.org/2000/svg"
                class="h-3 w-3"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                  clip-rule="evenodd"
                />
              </svg>
              <svg
                v-else
                xmlns="http://www.w3.org/2000/svg"
                class="h-3 w-3"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                  clip-rule="evenodd"
                />
              </svg>
            </button>
            <span v-else-if="!collapsed" class="w-4"></span>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5 text-indigo-600"
              :class="{ 'mr-2': !collapsed }"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
            </svg>
            <span v-if="!collapsed" class="text-gray-700 text-sm truncate flex-grow">{{
              node.name
            }}</span>
            <button
              v-if="!collapsed"
              @click.stop="openCreateModal(node._id, $event)"
              class="text-gray-400 hover:text-indigo-600 focus:outline-none opacity-0 group-hover:opacity-100 transition-opacity"
              title="Add subdirectory"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-3 w-3"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                  clip-rule="evenodd"
                />
              </svg>
            </button>
          </div>

          <!-- Directory contents (when expanded) -->
          <div v-if="!collapsed && node.isExpanded" class="pl-5 mt-1">
            <!-- Documents in this directory -->
            <div
              v-for="doc in directoryDocuments.get(node._id) || []"
              :key="doc.id"
              class="flex items-center py-2 px-2 rounded-md cursor-pointer hover:bg-indigo-50 transition-colors"
              @dblclick.stop="navigateToDocument(doc)"
            >
              <!-- File type icon -->
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 mr-2 text-blue-500"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
                  clip-rule="evenodd"
                />
              </svg>
              <span class="text-gray-700 text-sm truncate">{{ doc.title }}</span>
            </div>

            <!-- Child directories -->
            <template v-for="childNode in node.children" :key="childNode._id">
              <div
                class="flex items-center py-2 px-2 rounded-md cursor-pointer hover:bg-indigo-50 transition-colors group"
                :class="{ 'bg-indigo-100': currentDirectoryId === childNode._id }"
                @click.stop="toggleExpand(childNode, $event)"
                @dblclick.stop="navigateToDirectory(childNode._id)"
              >
                <button
                  v-if="
                    childNode.children.length > 0 ||
                    (directoryDocuments.get(childNode._id)?.length ?? 0) > 0
                  "
                  @click.stop="toggleExpand(childNode, $event)"
                  class="mr-1 text-gray-500 focus:outline-none"
                >
                  <svg
                    v-if="!childNode.isExpanded"
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-3 w-3"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  <svg
                    v-else
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-3 w-3"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                      clip-rule="evenodd"
                    />
                  </svg>
                </button>
                <span v-else class="w-4"></span>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-5 w-5 mr-2 text-indigo-600"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                </svg>
                <span class="text-gray-700 text-sm truncate flex-grow">{{ childNode.name }}</span>
                <button
                  @click.stop="openCreateModal(childNode._id, $event)"
                  class="text-gray-400 hover:text-indigo-600 focus:outline-none opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Add subdirectory"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-3 w-3"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                      clip-rule="evenodd"
                    />
                  </svg>
                </button>
              </div>

              <!-- Child directory contents (when expanded) -->
              <div v-if="childNode.isExpanded" class="pl-5 mt-1">
                <!-- Documents in child directory -->
                <div
                  v-for="doc in directoryDocuments.get(childNode._id) || []"
                  :key="doc.id"
                  class="flex items-center py-2 px-2 rounded-md cursor-pointer hover:bg-indigo-50 transition-colors"
                  @dblclick.stop="navigateToDocument(doc)"
                >
                  <!-- File type icon -->
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-5 w-5 mr-2 text-blue-500"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  <span class="text-gray-700 text-sm truncate">{{ doc.title }}</span>
                </div>

                <!-- Render nested child directories recursively -->
                <template v-if="childNode.children.length > 0">
                  <div
                    v-for="grandchildNode in childNode.children"
                    :key="grandchildNode._id"
                    class="flex items-center py-2 px-2 rounded-md cursor-pointer hover:bg-indigo-50 transition-colors group"
                    :class="{ 'bg-indigo-100': currentDirectoryId === grandchildNode._id }"
                    @click.stop="toggleExpand(grandchildNode, $event)"
                    @dblclick.stop="navigateToDirectory(grandchildNode._id)"
                  >
                    <button
                      v-if="
                        grandchildNode.children.length > 0 ||
                        (directoryDocuments.get(grandchildNode._id)?.length ?? 0) > 0
                      "
                      @click.stop="toggleExpand(grandchildNode, $event)"
                      class="mr-1 text-gray-500 focus:outline-none"
                    >
                      <svg
                        v-if="!grandchildNode.isExpanded"
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-3 w-3"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fill-rule="evenodd"
                          d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                          clip-rule="evenodd"
                        />
                      </svg>
                      <svg
                        v-else
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-3 w-3"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fill-rule="evenodd"
                          d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                          clip-rule="evenodd"
                        />
                      </svg>
                    </button>
                    <span v-else class="w-4"></span>
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-5 w-5 mr-2 text-indigo-600"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"
                      />
                    </svg>
                    <span class="text-gray-700 text-sm truncate flex-grow">{{
                      grandchildNode.name
                    }}</span>
                    <button
                      @click.stop="openCreateModal(grandchildNode._id, $event)"
                      class="text-gray-400 hover:text-indigo-600 focus:outline-none opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Add subdirectory"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-3 w-3"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fill-rule="evenodd"
                          d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                          clip-rule="evenodd"
                        />
                      </svg>
                    </button>
                  </div>
                </template>

                <!-- Grandchild directory contents -->
                <template
                  v-for="grandchildNode in childNode.children"
                  :key="`content-${grandchildNode._id}`"
                >
                  <div v-if="grandchildNode.isExpanded" class="pl-5 mt-1">
                    <!-- Documents in grandchild directory -->
                    <div
                      v-for="doc in directoryDocuments.get(grandchildNode._id) || []"
                      :key="doc.id"
                      class="flex items-center py-2 px-2 rounded-md cursor-pointer hover:bg-indigo-50 transition-colors"
                      @dblclick.stop="navigateToDocument(doc)"
                    >
                      <!-- File type icon -->
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="h-5 w-5 mr-2 text-blue-500"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fill-rule="evenodd"
                          d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
                          clip-rule="evenodd"
                        />
                      </svg>
                      <span class="text-gray-700 text-sm truncate">{{ doc.title }}</span>
                    </div>
                  </div>
                </template>
              </div>
            </template>
          </div>
        </div>
      </template>
    </div>

    <!-- Create Directory Modal -->
    <div
      v-if="showCreateModal"
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
            v-model="newDirectoryName"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Enter directory name"
            @keyup.enter="createDirectory"
          />
        </div>
        <div class="flex justify-end space-x-3">
          <button
            @click="showCreateModal = false"
            class="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 focus:outline-none"
          >
            Cancel
          </button>
          <button
            @click="createDirectory"
            class="px-4 py-2 text-white bg-indigo-600 rounded-md hover:bg-indigo-700 focus:outline-none"
            :disabled="!newDirectoryName.trim()"
          >
            Create
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.directory-tree {
  font-size: 0.875rem;
}
</style>
