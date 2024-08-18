<template>
  <div
    class="bg-gradient-to-br from-blue-50 to-indigo-100 p-8 shadow-lg rounded-xl border border-blue-200"
  >
    <h3 class="text-3xl font-extrabold mb-6 text-indigo-800 tracking-tight">Document Insights</h3>

    <!-- Model Selection Dropdown -->
    <div class="mb-6">
      <label for="model-select" class="block text-sm font-medium text-gray-700 mb-2"
        >Select Model</label
      >
      <div class="relative">
        <select
          id="model-select"
          v-model="selectedModel"
          class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
        >
          <optgroup label="OpenAI Models">
            <option value="gpt-4o-mini">GPT-4o Mini</option>
            <option value="gpt-4o" disabled>GPT-4o (Upgrade required)</option>
            <option value="gpt-4-turbo" disabled>GPT-4 Turbo (Upgrade required)</option>
            <option value="gpt-4" disabled>GPT-4 (Upgrade required)</option>
            <option value="gpt-3.5-turbo" disabled>GPT-3.5 Turbo (Upgrade required)</option>
          </optgroup>
          <optgroup label="Anthropic Models">
            <option value="claude-3.5-sonnet" disabled>Claude 3.5 Sonnet (Upgrade required)</option>
            <option value="claude-3-opus" disabled>Claude 3 Opus (Upgrade required)</option>
            <option value="claude-3-haiku" disabled>Claude 3 Haiku (Upgrade required)</option>
          </optgroup>
          <optgroup label="Meta Models">
            <option value="llama-3.1" disabled>LLama 3.1 (Upgrade required)</option>
            <option value="llama-3" disabled>LLama 3 (Upgrade required)</option>
          </optgroup>
        </select>
        <div class="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none">
          <svg
            class="h-5 w-5 text-gray-400"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fill-rule="evenodd"
              d="M10 3a1 1 0 01.707.293l3 3a1 1 0 01-1.414 1.414L10 5.414 7.707 7.707a1 1 0 01-1.414-1.414l3-3A1 1 0 0110 3zm-3.707 9.293a1 1 0 011.414 0L10 14.586l2.293-2.293a1 1 0 011.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
              clip-rule="evenodd"
            />
          </svg>
        </div>
      </div>
      <p class="mt-2 text-sm text-gray-500">
        Only GPT-4o Mini is available with your current plan. Upgrade to access more models.
      </p>
    </div>

    <button
      @click="generateSummary"
      class="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-6 py-4 rounded-lg font-bold text-lg transition duration-300 ease-in-out transform hover:from-blue-600 hover:to-indigo-700 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
      :disabled="isGenerating || !canGenerate"
    >
      <span v-if="isGenerating" class="flex items-center justify-center">
        <svg
          class="animate-spin -ml-1 mr-3 h-6 w-6 text-white"
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
        Crafting Your Summary...
      </span>
      <span v-else>Generate Document Insights with {{ selectedModel }}</span>
    </button>

    <transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0 translate-y-4"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-4"
    >
      <div
        v-if="formattedSummary"
        class="mt-8 bg-white p-6 rounded-lg shadow-inner border border-blue-100"
      >
        <h4 class="font-semibold text-xl mb-4 text-indigo-700">Summary:</h4>
        <div
          class="text-gray-700 leading-relaxed font-serif text-lg whitespace-pre-wrap"
          style="font-family: 'Georgia', serif"
          v-html="formattedSummary"
        ></div>
      </div>
    </transition>

    <transition
      enter-active-class="transition ease-out duration-300"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="error"
        class="mt-6 bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded-r-lg shadow-md"
        role="alert"
      >
        <p class="font-bold">Oops! Something went wrong</p>
        <p>{{ error }}</p>
      </div>
    </transition>
    <transition
      enter-active-class="transition ease-out duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="isGenerating" class="mt-6">
        <div class="relative pt-1">
          <div class="flex mb-2 items-center justify-between">
            <div>
              <span
                class="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-indigo-600 bg-indigo-200"
              >
                Progress
              </span>
            </div>
            <div class="text-right">
              <span class="text-xs font-semibold inline-block text-indigo-600">
                {{ progress }}%
              </span>
            </div>
          </div>
          <div class="overflow-hidden h-3 mb-4 text-xs flex rounded bg-indigo-200">
            <div
              :style="{ width: `${progress}%` }"
              class="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-gradient-to-r from-blue-500 to-indigo-600 transition-all duration-500 ease-in-out"
            ></div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>
<script lang="ts">
import { defineComponent, ref, onUnmounted, watch } from 'vue'
import axios from 'axios'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

interface WebSocketMessage {
  connection_id: string
  status: 'STARTED' | 'IN_PROGRESS' | 'COMPLETE' | 'ERROR'
  progress: number
  payload: {
    newText: string
    completeText: string
  }
}

export default defineComponent({
  name: 'SummarySection',
  props: {
    documentUploadId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const summary = ref('')
    const formattedSummary = ref('')
    const error = ref('')
    const isGenerating = ref(false)
    const progress = ref(0)
    const canGenerate = ref(true)
    const selectedModel = ref('gpt-4o-mini')
    let websocket: WebSocket | null = null
    let reconnectAttempts = 0
    const MAX_RECONNECT_ATTEMPTS = 5

    const updateFormattedSummary = async () => {
      try {
        const rawHtml = await marked(summary.value)
        formattedSummary.value = DOMPurify.sanitize(rawHtml)
      } catch (e) {
        console.error('Error formatting summary:', e)
        error.value = 'Error formatting summary. Please try again.'
      }
    }

    watch(summary, updateFormattedSummary)

    const resetState = () => {
      summary.value = ''
      formattedSummary.value = ''
      error.value = ''
      isGenerating.value = false
      progress.value = 0
      canGenerate.value = true
      if (websocket) {
        websocket.close()
        websocket = null
      }
    }

    watch(
      () => props.documentUploadId,
      (newId, oldId) => {
        if (newId !== oldId) {
          resetState()
        }
      }
    )

    const connectWebSocket = () => {
      websocket = new WebSocket(
        `ws://localhost:8000/ws/document-upload/${props.documentUploadId}/summary`
      )

      websocket.onopen = () => {
        console.log('WebSocket connected for summary')
        reconnectAttempts = 0
      }

      websocket.onmessage = (event) => {
        const data: WebSocketMessage = JSON.parse(event.data)
        console.log('WebSocket message:', data)

        progress.value = data.progress ? Math.round(data.progress) : data.progress

        if (data.status === 'COMPLETE') {
          summary.value = data.payload.completeText
          isGenerating.value = false
          progress.value = 100
          websocket?.close()
        } else if (data.status === 'IN_PROGRESS' && data.payload.newText) {
          summary.value += data.payload.newText
        } else if (data.status === 'ERROR') {
          handleError('An error occurred while generating the summary.')
        }
      }

      websocket.onerror = (event) => {
        console.error('WebSocket error:', event)
        handleError('Connection error. Please try again.')
      }

      websocket.onclose = (event) => {
        console.log('WebSocket disconnected:', event)
        if (isGenerating.value && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts++
          console.log(`Attempting to reconnect (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`)
          setTimeout(connectWebSocket, 3000) // Reconnect after 3 seconds
        } else if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
          handleError('Unable to maintain connection. Please try again later.')
        }
      }
    }
    const generateSummary = async () => {
      try {
        resetState()
        isGenerating.value = true
        canGenerate.value = false

        connectWebSocket()

        // Trigger summary generation with selected model
        await axios.post(`http://localhost:8000/documents/${props.documentUploadId}/summary`, {
          model: selectedModel.value
        })
      } catch (e) {
        handleError('Failed to generate summary. Please try again.')
      }
    }

    const handleError = (message: string) => {
      error.value = message
      isGenerating.value = false
      canGenerate.value = true
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.close()
      }
    }

    onUnmounted(() => {
      if (websocket) {
        websocket.close()
      }
    })

    return {
      summary,
      formattedSummary,
      error,
      isGenerating,
      progress,
      canGenerate,
      generateSummary,
      selectedModel,
      resetState
    }
  }
})
</script>
<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

.font-sans {
  font-family: 'Inter', sans-serif;
}

/* Custom styles for the dropdown */
select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
  background-position: right 0.5rem center;
  background-repeat: no-repeat;
  background-size: 1.5em 1.5em;
  padding-right: 2.5rem;
}

select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

optgroup {
  font-weight: bold;
  color: #4a5568;
}

option {
  font-weight: normal;
  color: #1a202c;
}

option:disabled {
  color: #a0aec0;
}
/* Add styles for markdown content */
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
