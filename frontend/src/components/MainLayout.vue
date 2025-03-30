<template>
  <div class="flex h-screen bg-gradient-to-br from-indigo-50 to-blue-100 overflow-hidden">
    <!-- Left Panel: Document Viewer -->
    <div
      :style="{ width: leftPanelWidth + 'px' }"
      class="bg-white shadow-xl overflow-auto transition-all duration-300 ease-in-out"
      @mouseup="handleTextSelection"
    >
      <div class="p-6">
        <div class="mt-6">
          <component
            :is="currentViewer"
            v-if="contentUrl"
            :contentUrl="contentUrl"
            class="rounded-lg shadow-inner border border-indigo-100"
          />
          <p v-else class="text-gray-500 text-center py-8">No content loaded</p>
        </div>
      </div>
    </div>

    <!-- Draggable Divider -->
    <div
      class="w-1 bg-indigo-300 cursor-col-resize hover:bg-indigo-400 active:bg-indigo-500 transition-colors duration-300"
      @mousedown="startDragging"
    ></div>

    <!-- Right Panel: Tools -->
    <div
      :style="{ width: rightPanelWidth + 'px' }"
      class="bg-white shadow-xl overflow-hidden transition-all duration-300 ease-in-out"
    >
      <div class="h-full flex flex-col">
        <!-- Tabs -->
        <div class="bg-indigo-100 px-4 py-2">
          <nav class="flex space-x-4" aria-label="Tabs">
            <button
              v-for="tab in tabs"
              :key="tab.name"
              @click="currentTab = tab.name"
              :class="[
                currentTab === tab.name
                  ? 'bg-white text-indigo-700 shadow'
                  : 'text-indigo-500 hover:text-indigo-700',
                'px-3 py-2 font-medium text-sm rounded-md transition-all duration-200'
              ]"
            >
              {{ tab.label }}
            </button>
          </nav>
        </div>

        <!-- Tab Content -->
        <div class="flex-grow overflow-auto p-6">
          <transition
            enter-active-class="transition ease-out duration-200"
            enter-from-class="opacity-0 translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition ease-in duration-150"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 translate-y-1"
          >
            <keep-alive>
              <component :is="currentTabComponent" :document-upload-id="safeDocumentId"></component>
            </keep-alive>
          </transition>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import {
  defineComponent,
  ref,
  computed,
  onMounted,
  onUnmounted,
  provide,
  nextTick,
  watch,
  defineAsyncComponent
} from 'vue'
import { useRouter } from 'vue-router'
import { useDocumentTitle } from '@/composables/useDocumentTitle'
// import DocumentUploadModal from './DocumentUploadModal.vue'
// import DocumentUploadModal from '@/components/DocumentUploadModal.vue'
const DocumentUploadModal = defineAsyncComponent(
  () => import('@/components/DocumentUploadModal.vue')
)
import SummaryAI from '@/components/SummaryAI.vue'
import HighlightExplain from './HighlightExplain.vue'
import ChatSection from './ChatSection.vue'
import PDFViewer from '@/components/Viewers/PDFViewer.vue'
import WebsiteViewer from '@/components/Viewers/WebsiteViewer.vue'
import EpubViewer from '@/components/Viewers/EpubViewer.vue'
import JSONViewer from '@/components/Viewers/JSONViewer.vue'
import MarkdownViewer from '@/components/Viewers/MarkdownViewer.vue'
import DocxViewer from '@/components/Viewers/DocxViewer.vue'
import SpreadsheetViewer from '@/components/Viewers/SpreadsheetViewer.vue'
import NotepadComponent from '@/components/NotepadComponent.vue'
import type { DocumentDetails } from '@/types'
import api from '@/api/axios'

export default defineComponent({
  name: 'MainLayout',
  components: {
    DocumentUploadModal,
    SummaryAI,
    HighlightExplain,
    ChatSection,
    PDFViewer,
    WebsiteViewer,
    EpubViewer,
    JSONViewer,
    MarkdownViewer,
    DocxViewer,
    SpreadsheetViewer,
    NotepadComponent
  },
  props: {
    documentId: {
      type: String,
      required: false
    }
  },
  setup(props) {
    const router = useRouter()
    const contentUrl = ref('')
    const currentTab = ref('summary')
    const leftPanelWidth = ref(window.innerWidth / 2)
    const rightPanelWidth = ref(window.innerWidth / 2)
    const isDragging = ref(false)
    const fileType = ref('')
    const selectedText = ref('')
    const fileName = ref('')

    // Use the document title composable
    const { documentTitle, documentUploadId, setDocumentTitle, setDocumentId } = useDocumentTitle()

    // Create a computed property for the document ID that is always a string or undefined (not null)
    const safeDocumentId = computed(() => documentUploadId.value || undefined)

    const tabs = [
      { name: 'summary', label: 'Summary', component: SummaryAI },
      { name: 'highlight', label: 'Highlight & Explain', component: HighlightExplain },
      { name: 'chat', label: 'Chat', component: ChatSection },
      { name: 'notepad', label: 'Notepad', component: NotepadComponent }
    ]

    const currentTabComponent = computed(() => {
      const tab = tabs.find((t) => t.name === currentTab.value)
      return tab ? tab.component : null
    })

    const handleTextSelection = () => {
      const selection = window.getSelection()
      if (selection && selection.toString().trim().length > 0) {
        selectedText.value = selection.toString().trim()
      }
    }

    provide('selectedText', selectedText)

    const currentViewer = computed(() => {
      if (!fileType.value) return null
      switch (fileType.value) {
        case 'application/pdf':
          return PDFViewer
        case 'application/epub+zip':
          return EpubViewer
        case 'application/json':
          return JSONViewer
        case 'text/plain':
        case 'text/markdown':
          return MarkdownViewer
        case 'docx':
          return DocxViewer
        case 'text/csv':
        case 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
          return SpreadsheetViewer
        case 'text/html':
          return WebsiteViewer
        case 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
          return DocxViewer
        default:
          console.warn('Unsupported file type?:', fileType.value)
          return null
      }
    })

    const handleDocumentLoaded = (documentData: any) => {
      console.log('Document loaded:', documentData)
      if (documentData.file) {
        contentUrl.value = URL.createObjectURL(documentData.file)
      } else {
        contentUrl.value = documentData.presigned_url || documentData.url || ''
      }
      const docId = documentData.id || documentData.document_upload_id
      setDocumentId(docId)
      fileType.value = documentData.file_type

      if (docId) {
        const newPath = `/uploads/${docId}/${documentData.url_friendly_file_name}/read`
        router.push(newPath)
      }

      fileName.value = documentData.file_name
      setDocumentTitle(documentData.title)
    }

    const startDragging = (e: MouseEvent) => {
      isDragging.value = true
      document.addEventListener('mousemove', onMouseMove)
      document.addEventListener('mouseup', stopDragging)
    }

    const stopDragging = () => {
      isDragging.value = false
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', stopDragging)
    }

    const onMouseMove = (e: MouseEvent) => {
      if (isDragging.value) {
        const newLeftWidth = e.clientX
        const newRightWidth = window.innerWidth - e.clientX
        if (newLeftWidth > 200 && newRightWidth > 200) {
          leftPanelWidth.value = newLeftWidth
          rightPanelWidth.value = newRightWidth
        }
      }
    }

    const fetchDocumentDetails = async (id: string) => {
      try {
        const response = await api.get<DocumentDetails>(`/document-uploads/${id}`)
        contentUrl.value = response.data.presigned_url
        setDocumentId(id)
        fileType.value = response.data.file_type
        fileName.value = response.data.file_name
        setDocumentTitle(response.data.title)
      } catch (error) {
        console.error('Error fetching document details:', error)
        // Handle error (e.g., show error message to user)
      }
    }

    const updatePanelWidths = () => {
      const totalWidth = window.innerWidth
      const leftRatio = leftPanelWidth.value / (leftPanelWidth.value + rightPanelWidth.value)
      leftPanelWidth.value = totalWidth * leftRatio
      rightPanelWidth.value = totalWidth - leftPanelWidth.value
    }

    onMounted(() => {
      window.addEventListener('resize', updatePanelWidths)
      if (props.documentId) {
        fetchDocumentDetails(props.documentId)
      }
    })

    onUnmounted(() => {
      window.removeEventListener('resize', updatePanelWidths)
    })

    return {
      contentUrl,
      documentUploadId,
      fileName,
      documentTitle,
      currentTab,
      tabs,
      currentTabComponent,
      currentViewer,
      leftPanelWidth,
      rightPanelWidth,
      handleDocumentLoaded,
      startDragging,
      fetchDocumentDetails,
      fileType,
      handleTextSelection,
      safeDocumentId
    }
  }
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.font-sans {
  font-family: 'Inter', sans-serif;
}
</style>
