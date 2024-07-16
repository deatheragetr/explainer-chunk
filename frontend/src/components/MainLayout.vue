<template>
  <div class="flex h-screen bg-gray-100">
    <!-- Left Panel: Document Viewer -->
    <div class="w-1/2 p-4 bg-white shadow-lg overflow-auto">
      <h2 class="text-2xl font-bold mb-4">Document Viewer</h2>

      <!-- Input for URL -->
      <div class="mb-4">
        <input 
          v-model="url"
          @keyup.enter="loadContent"
          class="w-full p-2 border rounded"
          placeholder="Enter PDF or website URL"
        />
        <button @click="loadContent" class="mt-2 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
          Load Content
        </button>
      </div>

      <!-- File input for PDF -->
      <input 
        type="file" 
        @change="handleFileUpload" 
        accept="application/pdf"
        class="mb-4"
      />


      <div v-if="fileError" class="text-red-500 mb-4">{{ fileError }}</div>
      <PDFViewer v-if="isPDF" :pdfUrl="pdfUrl" />
      <WebsiteViewer v-else-if="isWebsite" :websiteUrl="contentUrl" />
      <p v-else class="text-gray-500">No content loaded</p>
    </div>

    <!-- Right Panel: Tools -->
    <div class="w-1/2 p-4 space-y-4 overflow-auto">
      <!-- Summarize Section -->
      <div class="bg-white p-4 shadow rounded-lg">
        <h3 class="text-xl font-semibold mb-2">Summarize</h3>
        <button @click="summarize" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
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
        <button @click="highlightAndExplain" class="mt-2 bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
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
        <button @click="sendChatMessage" class="mt-2 bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600">
          Send
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref } from 'vue';
import PDFViewer from './PDFViewer.vue';
import WebsiteViewer from './WebsiteViewer.vue';

interface ChatMessage {
  sender: string;
  text: string;
}

export default defineComponent({
  name: 'MainLayout',
  components: {
    PDFViewer,
    WebsiteViewer
  },
  setup() {
    const url = ref('');
    const pdfUrl = ref<string | null>(null);
    const contentUrl = ref<string | null>(null);

    const isPDF = ref(false);
    const isWebsite = ref(false);

    const summary = ref<string | null>(null);
    const highlightText = ref('');
    const explanation = ref<string | null>(null);
    const chatInput = ref('');
    const chatMessages = ref<ChatMessage[]>([]);
    const fileError = ref<string | null>(null);

    const loadContent = () => {
      console.log("Loading content:", url.value);
      if (url.value) {
        contentUrl.value = url.value;
        isPDF.value = url.value.toLowerCase().endsWith('.pdf');
        isWebsite.value = !isPDF.value;
        fileError.value = null;
      }
    };

    const handleFileUpload = (event: Event) => {
      const file = (event.target as HTMLInputElement).files?.[0];
      if (file) {
        if (file.type !== 'application/pdf') {
          fileError.value = 'Please upload a PDF file.';
          pdfUrl.value = null;
          isPDF.value = false;
          isWebsite.value = false;
        } else {
          try {
            pdfUrl.value = URL.createObjectURL(file);
            fileError.value = null;
            isPDF.value = true;
            isWebsite.value = false;
            console.log('Created Blob URL:', pdfUrl.value);
          } catch (error) {
            console.error('Error creating Blob URL:', error);
            fileError.value = 'Error loading the file. Please try again.';
            pdfUrl.value = null;
            isPDF.value = false;
            isWebsite.value = false;
          }
        }
      } else {
        fileError.value = 'No file selected.';
        pdfUrl.value = null;
        isPDF.value = false;
        isWebsite.value = false;
      }

    };

    const summarize = () => {
      // TODO: Implement summarization logic
      summary.value = 'This is a placeholder summary of the document.';
    };

    const highlightAndExplain = () => {
      // TODO: Implement highlight and explain logic
      explanation.value = `Explanation for "${highlightText.value}": This is a placeholder explanation.`;
    };

    const sendChatMessage = () => {
      if (chatInput.value.trim()) {
        chatMessages.value.push({ sender: 'You', text: chatInput.value });
        // TODO: Implement chat logic / API call here
        chatMessages.value.push({ sender: 'AI', text: 'This is a placeholder response.' });
        chatInput.value = '';
      }
    };

    return {
      pdfUrl,
      url,
      summary,
      contentUrl,
      loadContent,
      isPDF,
      fileError,
      isWebsite,
      highlightText,
      explanation,
      chatInput,
      chatMessages,
      handleFileUpload,
      summarize,
      highlightAndExplain,
      sendChatMessage,
    };
  },
});
</script>