<template>
  <div
    class="bg-gradient-to-br from-blue-50 to-indigo-100 p-8 shadow-lg rounded-xl border border-blue-200"
  >
    <h3 class="text-3xl font-extrabold mb-6 text-indigo-800 tracking-tight">
      Highlight and Explain
    </h3>

    <!-- Model Selector -->
    <div class="mb-6">
      <ModelSelector v-model="selectedModel" />
    </div>

    <!-- Selected Text Display -->
    <div class="mb-6">
      <h4 class="text-lg font-semibold text-indigo-700 mb-2">Selected Text:</h4>
      <div
        v-if="selectedText"
        class="bg-white p-4 rounded-lg border border-indigo-200 shadow-inner max-h-48 overflow-auto"
      >
        <div
          class="text-gray-700 whitespace-pre-wrap break-words"
          v-html="formattedSelectedText"
        ></div>
      </div>
      <div
        v-else
        class="bg-white p-4 rounded-lg border border-indigo-200 shadow-inner flex items-center justify-center"
      >
        <p class="text-gray-500 italic flex items-center">
          <svg
            class="w-5 h-5 mr-2 text-indigo-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M13 10V3L4 14h7v7l9-11h-7z"
            ></path>
          </svg>
          Highlight text in the document to explain
        </p>
      </div>
    </div>

    <!-- Action Button -->
    <button
      @click="explainText"
      :disabled="!selectedText || isLoading"
      class="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-6 py-3 rounded-lg font-bold text-lg transition duration-300 ease-in-out transform hover:from-blue-600 hover:to-indigo-700 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <span v-if="isLoading" class="flex items-center justify-center">
        <svg
          class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          ></circle>
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
        Generating Explanation...
      </span>
      <span v-else>Explain Selected Text with {{ selectedModel }}</span>
    </button>

    <!-- Explanation Area -->
    <div
      v-if="explanation"
      class="mt-6 bg-white p-6 rounded-lg shadow-inner border border-blue-100 overflow-hidden"
    >
      <h4 class="font-semibold text-xl mb-4 text-indigo-700">Explanation:</h4>
      <div class="relative">
        <p
          class="text-gray-700 leading-relaxed"
          :class="{ 'animate-pulse': isLoading }"
          v-html="formattedExplanation"
        ></p>
        <div
          v-if="isLoading"
          class="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-indigo-600 animate-slide"
        ></div>
      </div>
    </div>

    <!-- Error Message -->
    <div
      v-if="error"
      class="mt-6 bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded-r-lg shadow-md"
      role="alert"
    >
      <p class="font-bold">Error</p>
      <p>{{ error }}</p>
    </div>

    <!-- Additional Actions -->
    <div v-if="explanation" class="mt-6 flex space-x-4">
      <button
        @click="copyExplanation"
        class="flex-1 bg-white text-indigo-600 border border-indigo-600 px-4 py-2 rounded-lg font-semibold transition duration-300 ease-in-out hover:bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
      >
        Copy Explanation
      </button>
      <button
        @click="resetComponent"
        class="flex-1 bg-gray-200 text-gray-700 px-4 py-2 rounded-lg font-semibold transition duration-300 ease-in-out hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
      >
        Reset
      </button>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, inject, watch, computed } from 'vue'
import { useToast } from 'vue-toastification'
import api from '@/api/axios'
import ModelSelector from './ModelSelector.vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

export default defineComponent({
  name: 'HighlightExplain',
  components: {
    ModelSelector
  },
  props: {
    documentUploadId: {
      type: String,
      required: false,
      default: null
    }
  },
  setup(props) {
    const selectedText = inject('selectedText', ref(''))
    const explanation = ref('')
    const formattedExplanation = ref('')
    const isLoading = ref(false)
    const selectedModel = ref('gpt-4o-mini')
    const error = ref('')
    let socket: WebSocket | null = null
    let reconnectAttempts = 0
    const MAX_RECONNECT_ATTEMPTS = 5

    const formattedSelectedText = computed(() => {
      if (!selectedText.value) return ''

      let formatted = selectedText.value
        .replace(/\n/g, '<br>')
        .replace(/ {2,}/g, (match) => '&nbsp;'.repeat(match.length))

      const maxLength = 3000
      if (formatted.length > maxLength) {
        formatted = formatted.slice(0, maxLength) + '...'
      }

      return DOMPurify.sanitize(`<span class="bg-yellow-200 px-1 rounded">${formatted}</span>`, {
        ALLOWED_TAGS: ['span', 'br'],
        ALLOWED_ATTR: ['class']
      })
    })

    watch(explanation, async (newExplanation) => {
      try {
        const html = await marked(newExplanation)
        formattedExplanation.value = DOMPurify.sanitize(html)
      } catch (err) {
        console.error('Error formatting explanation:', err)
        formattedExplanation.value = 'Error formatting explanation'
      }
    })

    const connectWebSocket = () => {
      if (!props.documentUploadId) {
        console.error('Cannot connect WebSocket: documentUploadId is null')
        handleError('Document ID is missing. Please try again.')
        return
      }

      socket = new WebSocket(
        `ws://localhost:8000/ws/document-upload/${props.documentUploadId}/text-explanation`
      )

      socket.onopen = () => {
        console.log('WebSocket connected for explanation')
        reconnectAttempts = 0
      }

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.status === 'COMPLETE') {
          explanation.value = data.payload.completeText
          isLoading.value = false
          socket?.close()
        } else if (data.status === 'IN_PROGRESS' && data.payload.newText) {
          explanation.value += data.payload.newText
        } else if (data.status === 'ERROR') {
          handleError('An error occurred while generating the explanation.')
        }
      }

      socket.onerror = (event) => {
        console.error('WebSocket error:', event)
        handleError('Connection error. Please try again.')
      }

      socket.onclose = (event) => {
        console.log('WebSocket disconnected:', event)
        if (isLoading.value && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts++
          console.log(`Attempting to reconnect (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`)
          setTimeout(connectWebSocket, 3000) // Reconnect after 3 seconds
        } else if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
          handleError('Unable to maintain connection. Please try again later.')
        }
      }
    }

    const explainText = async () => {
      if (!selectedText.value.trim()) {
        error.value = 'Please select text to explain'
        return
      }

      if (!props.documentUploadId) {
        error.value = 'Document ID is missing. Cannot explain text.'
        return
      }

      isLoading.value = true
      error.value = ''
      explanation.value = ''

      try {
        // Ensure WebSocket is connected
        if (!socket || socket.readyState !== WebSocket.OPEN) {
          connectWebSocket()
        }

        await api.post(`/documents/${props.documentUploadId}/explanation`, {
          highlighted_text: selectedText.value,
          model: selectedModel.value
        })
      } catch (err) {
        handleError('Failed to explain text. Please try again.')
      }
    }

    const handleError = (message: string) => {
      error.value = message
      isLoading.value = false
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close()
      }
    }

    const copyExplanation = () => {
      navigator.clipboard
        .writeText(explanation.value)
        .then(() => {
          // You could add a temporary "Copied!" message here
          console.log('Explanation copied to clipboard')
        })
        .catch((err) => {
          console.error('Failed to copy explanation: ', err)
        })
    }

    const resetComponent = () => {
      explanation.value = ''
      error.value = ''
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close()
      }
    }

    watch(selectedText, () => {
      explanation.value = ''
      error.value = ''
    })

    return {
      selectedText,
      formattedSelectedText,
      explanation,
      formattedExplanation,
      isLoading,
      explainText,
      selectedModel,
      error,
      copyExplanation,
      resetComponent
    }
  }
})
</script>

<style scoped>
@keyframes slide {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.animate-slide {
  animation: slide 1.5s linear infinite;
}

:deep(.markdown-body) {
  font-family: 'Georgia', serif;
  line-height: 1.6;
}

:deep(.markdown-body p) {
  margin-bottom: 1em;
}

:deep(.markdown-body h1),
:deep(.markdown-body h2),
:deep(.markdown-body h3),
:deep(.markdown-body h4),
:deep(.markdown-body h5),
:deep(.markdown-body h6) {
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
  color: #4a5568;
}

:deep(.markdown-body ul),
:deep(.markdown-body ol) {
  margin-bottom: 1em;
  padding-left: 2em;
}

:deep(.markdown-body li) {
  margin-bottom: 0.5em;
}

:deep(.markdown-body code) {
  background-color: #f0f0f0;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: 'Courier New', Courier, monospace;
}

:deep(.markdown-body pre) {
  background-color: #f0f0f0;
  padding: 1em;
  border-radius: 5px;
  overflow-x: auto;
}
</style>
