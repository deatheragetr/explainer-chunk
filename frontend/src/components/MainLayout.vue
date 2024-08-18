<template>
  <div class="flex h-screen bg-gray-100 relative">
    <!-- Left Panel: Document Viewer -->
    <div :style="{ width: leftPanelWidth + 'px' }" class="bg-white shadow-lg overflow-auto">
      <div class="p-4">
        <h2 class="text-2xl font-bold mb-4">Document Viewer</h2>

        <DocumentUploadModal @document-loaded="handleDocumentLoaded" />

        <PDFViewer v-if="isPDF" :pdfUrl="contentUrl" />
        <EpubViewer v-else-if="isEpub" :epubUrl="contentUrl" />
        <JSONViewer v-else-if="isJSON" :jsonUrl="contentUrl" />
        <MarkdownViewer v-else-if="isMarkdown" :markdownUrl="contentUrl" />
        <DocxViewer v-else-if="isDocx" :docxUrl="contentUrl" />
        <SpreadsheetViewer v-else-if="isSpreadsheet" :spreadsheetUrl="contentUrl" />
        <WebsiteViewer v-else-if="isWebsite" :websiteUrl="contentUrl" />

        <p v-else class="text-gray-500">No content loaded</p>
      </div>
    </div>

    <!-- Draggable Divider -->
    <div
      class="w-1 bg-gray-300 cursor-col-resize hover:bg-gray-400 active:bg-gray-500"
      @mousedown="startDragging"
    ></div>

    <!-- Right Panel: Tools -->
    <div :style="{ width: rightPanelWidth + 'px' }" class="p-4 space-y-4 overflow-auto">
      <!-- Summarize Section -->
      <SummaryAI :documentUploadId="documentUploadId" v-if="documentUploadId" />

      <!-- Highlight and Explain Section -->
      <div class="bg-white p-4 shadow rounded-lg">
        <h3 class="text-xl font-semibold mb-2">Highlight and Explain</h3>
        <input
          v-model="highlightText"
          @keyup.enter="highlightAndExplain"
          class="w-full p-2 border rounded"
          placeholder="Enter text to highlight and explain"
        />
        <button
          @click="highlightAndExplain"
          class="mt-2 bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
        >
          Highlight and Explain
        </button>
        <p v-if="explanation" class="mt-2">{{ explanation }}</p>
      </div>

      <!-- Chat Section -->
      <div class="bg-white p-4 shadow rounded-lg">
        <h3 class="text-xl font-semibold mb-2">Chat</h3>
        <div class="h-40 overflow-auto border p-2 mb-2">
          <div v-for="(message, index) in chatMessages" :key="index" class="mb-1">
            <strong>{{ message.sender }}:</strong> {{ message.text }}
          </div>
        </div>
        <input
          v-model="chatInput"
          @keyup.enter="sendChatMessage"
          class="w-full p-2 border rounded"
          placeholder="Type your question here"
        />
        <button
          @click="sendChatMessage"
          class="mt-2 bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600"
        >
          Send
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, type Ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

import PDFViewer from '@/components/Viewers/PDFViewer.vue'
import WebsiteViewer from '@/components/Viewers/WebsiteViewer.vue'
import EpubViewer from '@/components/Viewers/EpubViewer.vue'
import JSONViewer from '@/components/Viewers/JSONViewer.vue'
import MarkdownViewer from '@/components/Viewers/MarkdownViewer.vue'
import DocxViewer from '@/components/Viewers/DocxViewer.vue'
import SpreadsheetViewer from '@/components/Viewers/SpreadsheetViewer.vue'
import SummaryAI from '@/components/SummaryAI.vue'
import DocumentUploadModal from './DocumentUploadModal.vue'
import type { DocumentUploadData } from '@/types'

interface ChatMessage {
  sender: string
  text: string
}

interface DocumentDetails {
  presigned_url: string
  file_type: string
}

interface ImportProgress {
  task_id?: string
  connection_id?: string
  status: string
  progress: number | null
  payload: {
    presigned_url?: string
    file_type?: string
    document_upload_id?: string
    url_friendly_file_name?: string
  }
}

export default defineComponent({
  name: 'MainLayout',
  components: {
    PDFViewer,
    WebsiteViewer,
    EpubViewer,
    JSONViewer,
    DocxViewer,
    SpreadsheetViewer,
    MarkdownViewer,
    SummaryAI,
    DocumentUploadModal
  },
  props: {
    documentId: {
      type: String,
      required: false
    }
  },

  setup(props) {
    const router = useRouter()
    const url = ref('')
    const contentUrl = ref<string>('')

    const isPDF = ref(false)
    const isJSON = ref(false)
    const isWebsite = ref(false)
    const isEpub = ref(false)
    const isMarkdown = ref(false)
    const isDocx = ref(false)
    const isSpreadsheet = ref(false)

    const summary = ref<string | null>(null)
    const highlightText = ref('')
    const explanation = ref<string | null>(null)
    const chatInput = ref('')
    const chatMessages = ref<ChatMessage[]>([])
    const error = ref<string | null>(null)
    const isOpen = ref(false)
    const documentUploadId = ref<string | null>(null)

    // Status loading bar data
    const importProgress = ref<ImportProgress | null>(null)

    // Website capture related
    const websocket = ref<WebSocket | null>(null)

    // Used for reactive dragging.
    const leftPanelWidth = ref(window.innerWidth / 2)
    const rightPanelWidth = ref(window.innerWidth / 2)
    const isDragging = ref(false)

    const isDialogButtonDisabled = computed(() => {
      return !!importProgress.value && importProgress.value.status !== 'COMPLETE'
    })

    const handleDocumentLoaded = (documentData: DocumentUploadData) => {
      console.log('DOCUMENT DATA: ', documentData)
      if (documentData.file) {
        contentUrl.value = URL.createObjectURL(documentData.file)
      } else {
        contentUrl.value = documentData.presigned_url || documentData.url || ''
      }
      documentUploadId.value = documentData.id || documentData.document_upload_id
      updateFileType(documentData.file_type)
      const newPath = `/uploads/${documentData.id || documentData.document_upload_id}/${documentData.url_friendly_file_name}/read`

      router.push(newPath)
    }

    const fetchDocumentDetails = async (id: string) => {
      try {
        const response = await axios.get<DocumentDetails>(
          `http://localhost:8000/document-uploads/${id}`
        )
        contentUrl.value = response.data.presigned_url
        updateFileType(response.data.file_type)
        documentUploadId.value = id
      } catch (error) {
        console.error('Error fetching document details:', error)
        // Handle error (e.g., show error message to user)
      }
    }

    const updateFileType = (type: string) => {
      resetFileTypes(null)
      isPDF.value = type === 'application/pdf'
      isJSON.value = type === 'application/json'
      isWebsite.value = type.startsWith('text/html')
      isEpub.value = type === 'application/epub+zip'
      isMarkdown.value = type === 'text/markdown' || type === 'text/plain'
      isDocx.value =
        type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      isSpreadsheet.value =
        type === 'text/csv' ||
        type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }

    const startDragging = () => {
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

        // Ensure minimum width for both panels
        if (newLeftWidth > 200 && newRightWidth > 200) {
          leftPanelWidth.value = newLeftWidth
          rightPanelWidth.value = newRightWidth
        }
      }
    }

    onMounted(() => {
      window.addEventListener('resize', updatePanelWidths)
      if (props.documentId) {
        fetchDocumentDetails(props.documentId)
      }
    })

    onUnmounted(() => {
      window.removeEventListener('resize', updatePanelWidths)
      if (websocket.value) {
        websocket.value.close()
      }
    })

    const updatePanelWidths = () => {
      const totalWidth = window.innerWidth
      const leftRatio = leftPanelWidth.value / (leftPanelWidth.value + rightPanelWidth.value)
      leftPanelWidth.value = totalWidth * leftRatio
      rightPanelWidth.value = totalWidth - leftPanelWidth.value
    }

    const openModal = () => {
      isOpen.value = true
    }

    const closeModal = () => {
      isOpen.value = false
      error.value = null
      url.value = ''
      importProgress.value = null
    }

    const resetFileTypes = (currentRef: Ref<boolean> | null) => {
      const fileTypes: Ref<boolean>[] = [
        isPDF,
        isWebsite,
        isEpub,
        isJSON,
        isMarkdown,
        isDocx,
        isSpreadsheet
      ]

      fileTypes.forEach((refObj) => {
        refObj.value = refObj === currentRef
      })
    }

    const summarize = () => {
      // TODO: Implement summarization logic
      summary.value = 'This is a placeholder summary of the document.'
    }

    const highlightAndExplain = () => {
      // TODO: Implement highlight and explain logic
      explanation.value = `Explanation for "${highlightText.value}": This is a placeholder explanation.`
    }

    const sendChatMessage = () => {
      if (chatInput.value.trim()) {
        chatMessages.value.push({ sender: 'You', text: chatInput.value })
        // TODO: Implement chat logic / API call here
        chatMessages.value.push({ sender: 'AI', text: 'This is a placeholder response.' })
        chatInput.value = ''
      }
    }

    return {
      url,
      error,
      isOpen,
      openModal,
      closeModal,
      summary,
      contentUrl,
      // loadContent,
      isPDF,
      isEpub,
      isJSON,
      isMarkdown,
      isDocx,
      isWebsite,
      isSpreadsheet,
      highlightText,
      explanation,
      chatInput,
      chatMessages,
      // handleFileUpload,
      summarize,
      highlightAndExplain,
      sendChatMessage,
      resetFileTypes,
      leftPanelWidth,
      rightPanelWidth,
      startDragging,
      fetchDocumentDetails,
      updateFileType,
      importProgress,
      // captureWebsite,
      isDialogButtonDisabled,
      documentUploadId,
      handleDocumentLoaded
    }
  }
})
</script>
<style>
/* Disable text selection while dragging */
.user-select-none {
  user-select: none;
}
</style>
