<template>
  <div class="flex h-screen bg-gray-100">
    <!-- Left Panel: Document Viewer -->
    <div class="w-1/2 p-4 bg-white shadow-lg overflow-auto">
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
      <p v-else class="text-gray-500">No content loaded</p>
    </div>

    <!-- Right Panel: Tools -->
    <div class="w-1/2 p-4 space-y-4 overflow-auto">
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
                    accept="application/pdf, application/epub+zip, application/json"
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
import { defineComponent, ref, Ref } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import PDFViewer from './Viewers/PDFViewer.vue'
import WebsiteViewer from './Viewers/WebsiteViewer.vue'
import EpubViewer from './Viewers/EpubViewer.vue'
import JSONViewer from './Viewers/JSONViewer.vue'

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
    Dialog,
    DialogPanel,
    DialogTitle,
    TransitionChild,
    TransitionRoot
  },
  setup() {
    const url = ref('')
    const contentUrl = ref<string | null>(null)

    const isPDF = ref(false)
    const isJSON = ref(false)
    const isWebsite = ref(false)
    const isEpub = ref(false)

    const summary = ref<string | null>(null)
    const highlightText = ref('')
    const explanation = ref<string | null>(null)
    const chatInput = ref('')
    const chatMessages = ref<ChatMessage[]>([])
    const error = ref<string | null>(null)
    const isOpen = ref(false)

    const fileType = ref<string | null>(null)
    const fileContent = ref<string | null>(null)

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
      const fileTypes: Ref<boolean>[] = [isPDF, isWebsite, isEpub, isJSON]

      fileTypes.forEach((refObj) => {
        refObj.value = refObj === currentRef
      })
    }

    const handleFileUpload = (event: Event) => {
      const file = (event.target as HTMLInputElement).files?.[0]
      if (file) {
        const extension = file.name.split('.').pop()?.toLowerCase()
        fileType.value = extension || null

        console.log('Uploading file of type: ', file.type)
        console.log('And extension: ', fileType.value)

        try {
          if (file.type) {
            switch (file.type) {
              case 'application/pdf':
                contentUrl.value = URL.createObjectURL(file)
                resetFileTypes(isPDF)
                break
              case 'application/epub+zip':
                contentUrl.value = URL.createObjectURL(file)
                resetFileTypes(isEpub)
                break
              case 'application/json':
                contentUrl.value = URL.createObjectURL(file)
                resetFileTypes(isJSON)
                break
            }
          } else {
            switch (extension) {
              case 'pdf':
                contentUrl.value = URL.createObjectURL(file)
                resetFileTypes(isPDF)
                break
              case 'txt':
              case 'md':
              case 'json':
                contentUrl.value = URL.createObjectURL(file)
                resetFileTypes(isJSON)
                break
              case 'xml':
              case 'docx':
                // Use mammoth.js to extract text
                // const result = await mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() });
                // fileContent.value = result.value;
                break
              case 'epub':
                contentUrl.value = URL.createObjectURL(file)
                resetFileTypes(isEpub)
                break
              case 'csv':
              case 'xlsx':
                // Use xlsx library to parse spreadsheet
                // const workbook = XLSX.read(await file.arrayBuffer(), { type: 'array' });
                // fileContent.value = workbook.SheetNames.map(sheetName => {
                //   const sheet = workbook.Sheets[sheetName];
                //   return XLSX.utils.sheet_to_csv(sheet);
                // }).join('\n\n');
                break
              // ... handle other file types ...
              default:
                resetFileTypes(null)
                throw new Error('Unsupported file type')
            }
          }
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
      isWebsite,
      highlightText,
      explanation,
      chatInput,
      chatMessages,
      handleFileUpload,
      summarize,
      highlightAndExplain,
      sendChatMessage,
      resetFileTypes
    }
  }
})
</script>
