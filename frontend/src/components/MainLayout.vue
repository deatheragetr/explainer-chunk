<template>
  <div class="flex h-screen bg-gray-100 relative">
    <!-- Left Panel: Document Viewer -->
    <div :style="{ width: leftPanelWidth + 'px' }" class="bg-white shadow-lg overflow-auto">
      <div class="p-4">
        <h2 class="text-2xl font-bold mb-4">Document Viewer</h2>

        <button
          @click="openModal"
          class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 mb-4"
        >
          Add Website or Document
        </button>

        <PDFViewer v-if="isPDF" :pdfUrl="contentUrl" />
        <WebsiteViewer v-else-if="isWebsite" :websiteUrl="contentUrl" />
        <EpubViewer v-else-if="isEpub" :epubUrl="contentUrl" />
        <JSONViewer v-else-if="isJSON" :jsonUrl="contentUrl" />
        <MarkdownViewer v-else-if="isMarkdown" :markdownUrl="contentUrl" />
        <DocxViewer v-else-if="isDocx" :docxUrl="contentUrl" />
        <SpreadsheetViewer v-else-if="isSpreadsheet" :spreadsheetUrl="contentUrl" />

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
      <div class="bg-white p-4 shadow rounded-lg">
        <h3 class="text-xl font-semibold mb-2">Summarize</h3>
        <button
          @click="summarize"
          class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        >
          Summarize Document
        </button>
        <p v-if="summary" class="mt-2">{{ summary }}</p>
      </div>

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

    <!-- Modal -->
    <TransitionRoot appear :show="isOpen" as="template">
      <Dialog as="div" @close="closeModal" class="relative z-10">
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
                <DialogTitle as="h3" class="text-lg font-medium leading-6 text-gray-900">
                  Add Website or Document
                </DialogTitle>
                <div class="mt-2">
                  <!-- External URI upload -->
                  <input
                    v-model="url"
                    @keyup.enter="loadContent"
                    class="w-full p-2 border rounded mb-2"
                    placeholder="Enter PDF or website URL"
                  />

                  <!-- File input in the modal -->
                  <input
                    type="file"
                    @change="handleFileUpload"
                    accept="application/pdf, application/epub+zip, application/json, text/markdown, text/plain, .md, .markdown, .txt, .json, .pdf, .docx, .csv, .xlsx"
                    class="mb-2"
                  />
                  <p v-if="error" class="text-red-500 mb-2">{{ error }}</p>
                </div>

                <div class="mt-4">
                  <button
                    type="button"
                    class="inline-flex justify-center rounded-md border border-transparent bg-blue-100 px-4 py-2 text-sm font-medium text-blue-900 hover:bg-blue-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                    @click="loadContent"
                  >
                    Load Content
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, Ref, onMounted, onUnmounted } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import axios from 'axios'
import PDFViewer from './Viewers/PDFViewer.vue'
import WebsiteViewer from './Viewers/WebsiteViewer.vue'
import EpubViewer from './Viewers/EpubViewer.vue'
import JSONViewer from './Viewers/JSONViewer.vue'
import MarkdownViewer from './Viewers/MarkdownViewer.vue'
import DocxViewer from './Viewers/DocxViewer.vue'
import SpreadsheetViewer from './Viewers/SpreadsheetViewer.vue'
import { uploadLargeFile } from '@/utils/fileUpload'

interface ChatMessage {
  sender: string
  text: string
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
    Dialog,
    DialogPanel,
    DialogTitle,
    TransitionChild,
    TransitionRoot,
    MarkdownViewer
  },
  setup() {
    const url = ref('')
    const contentUrl = ref<string | null>(null)

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

    // Used for reactive dragging.
    const leftPanelWidth = ref(window.innerWidth / 2)
    const rightPanelWidth = ref(window.innerWidth / 2)
    const isDragging = ref(false)

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

        // Ensure minimum width for both panels
        if (newLeftWidth > 200 && newRightWidth > 200) {
          leftPanelWidth.value = newLeftWidth
          rightPanelWidth.value = newRightWidth
        }
      }
    }

    onMounted(() => {
      window.addEventListener('resize', updatePanelWidths)
    })

    onUnmounted(() => {
      window.removeEventListener('resize', updatePanelWidths)
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
    }

    const loadContent = () => {
      console.log('Loading content:', url.value)
      error.value = null
      if (url.value) {
        try {
          // TODO: Import into correct doc type e.g., http://example.org/foo.pdf?
          resetFileTypes(null)
          contentUrl.value = url.value
          isWebsite.value = true
          closeModal()
        } catch (e) {
          error.value = 'Invalid URL. Please enter a valid URL.'
        }
      } else {
        error.value = 'Please enter a URL'
      }
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

    const handleFileUpload = async (event: Event) => {
      const file = (event.target as HTMLInputElement).files?.[0]
      if (file) {
        try {
          let fileSupported: Boolean = false
          let fileType = ''
          if (file.type) {
            fileSupported = true
            switch (file.type) {
              case 'application/pdf':
                resetFileTypes(isPDF)
                break
              case 'application/epub+zip':
                resetFileTypes(isEpub)
                break
              case 'application/json':
                resetFileTypes(isJSON)
                break
              case 'text/markdown':
              case 'text/plain': // This will catch .txt files
                resetFileTypes(isMarkdown)
                break
              case 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                resetFileTypes(isDocx)
                break
              case 'text/csv':
              case 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                resetFileTypes(isSpreadsheet)
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
                resetFileTypes(isPDF)
                fileType = 'application/pdf'
                break
              case 'json':
                resetFileTypes(isJSON)
                fileType = 'application/json'
                break
              // case 'xml':
              case 'epub':
                resetFileTypes(isEpub)
                fileType = 'application/epub+zip'
                break
              case 'csv':
              case 'xlsx':
                resetFileTypes(isSpreadsheet)
                fileType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                break
              case 'md':
              case 'markdown':
                resetFileTypes(isMarkdown)
                fileType = 'text/markdown'
                break
              case 'txt': // Explicitly handle .txt files as Markdown
                resetFileTypes(isMarkdown)
                fileType = 'text/plain'
                break
              case 'docx':
                resetFileTypes(isDocx)
                fileType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                break
              // ... handle other file types ...
              default:
                resetFileTypes(null)
                throw new Error('Unsupported file type')
            }
          }

          const { data: uploadData } = await uploadLargeFile(file, fileType)
          console.log('UPLOAD DATA?: ', uploadData)

          // const { data: uploadData } = await axios.post('http://localhost:8000/upload-url/', {
          //   filename: file.name,
          //   file_type: fileType
          // })

          // const maxRetries = 3
          // for (let i = 0; i < maxRetries; i++) {
          //   try {
          //     await axios.put(uploadData.presigned_url, file, {
          //       headers: {
          //         'Content-Type': fileType
          //       },
          //       // Increase timeout for large files
          //       timeout: 30000 // 30 seconds
          //     })
          //     break // Success, exit retry loop
          //   } catch (uploadError) {
          //     if (i === maxRetries - 1) throw uploadError // Rethrow on last attempt
          //     console.log(`Upload attempt ${i + 1} failed, retrying...`)
          //     await new Promise((resolve) => setTimeout(resolve, 1000)) // Wait 1 second before retrying
          //   }
          // }

          // await axios.post('http://localhost:8000/document-uploads/', {
          //   file_name: file.name,
          //   file_type: fileType,
          //   file_key: uploadData.file_key
          // })

          contentUrl.value = URL.createObjectURL(file)
          error.value = null
          closeModal()
        } catch (e) {
          error.value = `Error loading the file: ${e instanceof Error ? e.message : String(e)}`
        }
      } else {
        error.value = 'No file selected.'
      }
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
      loadContent,
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
      handleFileUpload,
      summarize,
      highlightAndExplain,
      sendChatMessage,
      resetFileTypes,
      leftPanelWidth,
      rightPanelWidth,
      startDragging
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
