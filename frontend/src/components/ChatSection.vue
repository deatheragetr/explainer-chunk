<template>
  <div
    class="bg-gradient-to-br from-blue-50 to-indigo-100 p-8 shadow-lg rounded-xl border border-blue-200 h-full flex flex-col"
  >
    <h3 class="text-3xl font-extrabold mb-6 text-indigo-800 tracking-tight">Chat with Document</h3>

    <!-- Model Selector -->
    <div class="mb-4">
      <ModelSelector v-model="selectedModel" @change="handleModelChange" />
    </div>

    <!-- Chat Messages -->
    <div
      ref="chatContainer"
      class="flex-grow bg-white p-4 rounded-lg shadow-inner border border-blue-100 overflow-y-auto mb-4 transition-all duration-300 ease-in-out"
      @scroll="handleScroll"
    >
      <!-- No More History Message -->
      <div v-if="noMoreHistory" class="text-center text-gray-500 my-4">
        <p>No more chat history available.</p>
      </div>

      <!-- Loading Older Messages Indicator -->
      <div v-if="isLoadingOlder" class="text-center text-gray-500 my-4">
        <div class="loading-ellipsis">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <p>Loading older messages...</p>
      </div>

      <TransitionGroup name="fade">
        <div v-for="message in chatMessages" :key="message.message_id" class="mb-6 animate-fade-in">
          <div
            :class="[
              'p-4 rounded-lg shadow transition-all duration-300 ease-in-out transform hover:scale-102',
              message.role === 'user' ? 'bg-indigo-100 ml-12' : 'bg-gray-100 mr-12'
            ]"
          >
            <p
              class="font-semibold mb-2 text-lg"
              :class="message.role === 'user' ? 'text-indigo-700' : 'text-gray-700'"
            >
              {{ message.role === 'user' ? 'You' : 'AI' }}
            </p>
            <div
              class="text-gray-800 whitespace-pre-wrap chat-message"
              v-html="formatMessage(message.content)"
            ></div>
          </div>
        </div>
      </TransitionGroup>

      <!-- Calm Loading Animation for New Messages -->
      <div v-if="isLoading" class="flex items-center justify-center h-12 mb-6">
        <div class="loading-ellipsis">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="flex items-center space-x-2">
      <input
        v-model="userInput"
        @keyup.enter="sendMessage"
        type="text"
        placeholder="Type your message here..."
        class="flex-grow p-3 border border-gray-300 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-300 ease-in-out text-lg"
      />
      <button
        @click="sendMessage"
        :disabled="!userInput.trim() || isLoading"
        class="bg-gradient-to-r from-indigo-500 to-blue-600 text-white px-6 py-3 rounded-r-lg font-semibold transition-all duration-300 ease-in-out transform hover:from-indigo-600 hover:to-blue-700 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 shadow-md disabled:opacity-50 disabled:cursor-not-allowed text-lg"
      >
        <span v-if="isLoading" class="flex items-center">
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
          Sending...
        </span>
        <span v-else>Send</span>
      </button>
    </div>

    <!-- Error Message -->
    <div
      v-if="error"
      class="mt-4 bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded-r-lg shadow-md text-lg"
      role="alert"
    >
      <p class="font-bold">Error</p>
      <p>{{ error }}</p>
    </div>
  </div>
</template>

<script lang="ts">
import {
  defineComponent,
  ref,
  onMounted,
  onUnmounted,
  watch,
  nextTick,
  onActivated,
  onDeactivated
} from 'vue'
import axios from 'axios'
import ModelSelector from './ModelSelector.vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

interface ChatMessage {
  message_id: string
  content: string
  role: 'user' | 'assistant'
  created_at: string
  conversation_id: string
}

export default defineComponent({
  name: 'ChatSection',
  components: {
    ModelSelector
  },
  props: {
    documentUploadId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const chatMessages = ref<ChatMessage[]>([])
    const userInput = ref('')
    const selectedModel = ref('gpt-4o-mini')
    const isLoading = ref(false)
    const isLoadingOlder = ref(false)
    const error = ref('')
    const chatContainer = ref<HTMLElement | null>(null)
    const nextBefore = ref<string | null>(null)
    const noMoreHistory = ref(false)
    let socket: WebSocket | null = null
    let reconnectAttempts = 0
    const MAX_RECONNECT_ATTEMPTS = 5
    const scrollPosition = ref(0)
    const isInitialLoad = ref(true)

    const saveScrollPosition = () => {
      if (chatContainer.value) {
        scrollPosition.value = chatContainer.value.scrollTop
      }
    }

    const restoreScrollPosition = () => {
      nextTick(() => {
        if (chatContainer.value) {
          chatContainer.value.scrollTop = scrollPosition.value
        }
      })
    }

    const connectWebSocket = () => {
      socket = new WebSocket(
        `ws://localhost:8000/ws/document-upload/${props.documentUploadId}/chat`
      )

      socket.onopen = () => {
        console.log('WebSocket connected for chat')
        reconnectAttempts = 0
      }

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.status === 'COMPLETE') {
          if (data.payload.completeText) {
            updateChatMessages(data.payload.completeText, true)
          }
          isLoading.value = false
        } else if (data.status === 'IN_PROGRESS' && data.payload.newText) {
          updateChatMessages(data.payload.newText)
        } else if (data.status === 'ERROR') {
          handleError('An error occurred while processing your message.')
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

    const updateChatMessages = (text: string, replace: boolean = false) => {
      if (
        chatMessages.value.length === 0 ||
        chatMessages.value[chatMessages.value.length - 1].role !== 'assistant'
      ) {
        // Start a new assistant message
        const newMessage: ChatMessage = {
          message_id: `temp-${Date.now()}`,
          content: text,
          role: 'assistant',
          created_at: new Date().toISOString(),
          conversation_id: props.documentUploadId
        }
        chatMessages.value.push(newMessage)
      } else {
        // Update the existing assistant message
        const lastMessage = chatMessages.value[chatMessages.value.length - 1]
        if (replace) {
          // Replace the entire content when the message is complete
          lastMessage.content = text
        } else {
          // Append the new text for incremental updates
          lastMessage.content += text
        }
      }
      scrollToBottom(true)
    }

    const scrollToBottom = (smooth = false) => {
      nextTick(() => {
        if (chatContainer.value) {
          chatContainer.value.scrollTo({
            top: chatContainer.value.scrollHeight,
            behavior: smooth ? 'smooth' : 'auto'
          })
        }
      })
    }

    const sendMessage = async () => {
      if (userInput.value.trim() && !isLoading.value) {
        isLoading.value = true
        error.value = ''
        const userMessage = userInput.value.trim()
        const newMessage: ChatMessage = {
          message_id: `temp-${Date.now()}`,
          content: userMessage,
          role: 'user',
          created_at: new Date().toISOString(),
          conversation_id: props.documentUploadId
        }
        chatMessages.value.push(newMessage)
        userInput.value = ''

        try {
          // Ensure WebSocket is connected
          if (!socket || socket.readyState !== WebSocket.OPEN) {
            connectWebSocket()
          }
          await axios.post(
            `http://localhost:8000/documents/${props.documentUploadId}/chat/messages`,
            {
              message_content: userMessage,
              model: selectedModel.value
            }
          )

          scrollToBottom(true)
        } catch (err) {
          handleError('Failed to send message. Please try again.')
        }
      }
    }

    const handleError = (message: string) => {
      error.value = message
      isLoading.value = false
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close()
      }
    }

    const formatMessage = (text: string) => {
      const html = marked.parse(text)
      return DOMPurify.sanitize(html)
    }

    const fetchChatHistory = async (before: string | null = null) => {
      try {
        const response = await axios.get(
          `http://localhost:8000/documents/${props.documentUploadId}/chat/messages`,
          {
            params: {
              model: selectedModel.value,
              before: before,
              limit: 50
            }
          }
        )
        return response.data
      } catch (err) {
        console.error('Failed to fetch chat history:', err)
        handleError('Failed to load chat history. Please try again.')
        return null
      }
    }

    const loadInitialChatHistory = async () => {
      const history = await fetchChatHistory()
      if (history) {
        chatMessages.value = history.messages.reverse()
        nextBefore.value = history.next_before
        noMoreHistory.value = !history.next_before
        scrollToBottom()
      }
    }

    const loadOlderMessages = async () => {
      if (isLoadingOlder.value || noMoreHistory.value) return

      isLoadingOlder.value = true
      const history = await fetchChatHistory(nextBefore.value)
      isLoadingOlder.value = false

      if (history) {
        const previousHeight = chatContainer.value?.scrollHeight || 0
        const newMessages = history.messages
          .reverse()
          .filter(
            (msg: ChatMessage) =>
              !chatMessages.value.some((existingMsg) => existingMsg.message_id === msg.message_id)
          )
        chatMessages.value = [...newMessages, ...chatMessages.value]
        nextBefore.value = history.next_before
        noMoreHistory.value = !history.next_before

        nextTick(() => {
          if (chatContainer.value) {
            const newHeight = chatContainer.value.scrollHeight
            chatContainer.value.scrollTop = newHeight - previousHeight
          }
        })
      }
    }

    const handleScroll = () => {
      if (chatContainer.value) {
        const { scrollTop } = chatContainer.value
        if (scrollTop === 0 && !isLoadingOlder.value && !noMoreHistory.value) {
          loadOlderMessages()
        }
      }
    }

    const handleModelChange = async () => {
      chatMessages.value = []
      nextBefore.value = null
      noMoreHistory.value = false
      await loadInitialChatHistory()
    }

    onMounted(() => {
      if (isInitialLoad.value) {
        loadInitialChatHistory().then(() => {
          scrollToBottom()
          isInitialLoad.value = false
        })
      }
    })

    onActivated(() => {
      if (!isInitialLoad.value) {
        restoreScrollPosition()
      }
    })

    onDeactivated(() => {
      saveScrollPosition()
    })

    onUnmounted(() => {
      if (socket) {
        socket.close()
      }
    })

    watch(chatMessages, () => {
      if (
        chatContainer.value &&
        chatContainer.value.scrollHeight -
          (chatContainer.value.scrollTop + chatContainer.value.clientHeight) <
          100
      ) {
        scrollToBottom(true)
      }
    })

    return {
      chatMessages,
      userInput,
      sendMessage,
      selectedModel,
      isLoading,
      isLoadingOlder,
      error,
      formatMessage,
      chatContainer,
      noMoreHistory,
      handleScroll,
      handleModelChange,
      saveScrollPosition,
      restoreScrollPosition
    }
  }
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fadeIn 0.5s ease-out forwards;
}

.hover\:scale-102:hover {
  transform: scale(1.02);
}

.chat-message {
  font-size: 1.125rem; /* 18px */
  line-height: 1.75;
  color: #1a202c; /* Tailwind's gray-900 for better contrast */
}

:deep(.markdown-body) {
  font-family:
    'Inter',
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    Roboto,
    Oxygen,
    Ubuntu,
    Cantarell,
    'Open Sans',
    'Helvetica Neue',
    sans-serif;
  line-height: 1.8;
  font-size: 1.125rem; /* 18px */
}

:deep(.markdown-body p) {
  margin-bottom: 1.25em;
}

:deep(.markdown-body h1),
:deep(.markdown-body h2),
:deep(.markdown-body h3),
:deep(.markdown-body h4),
:deep(.markdown-body h5),
:deep(.markdown-body h6) {
  margin-top: 1.5em;
  margin-bottom: 0.75em;
  font-weight: 600;
  color: #2d3748; /* Tailwind's gray-800 for better contrast */
  line-height: 1.3;
}

:deep(.markdown-body h1) {
  font-size: 2em;
}
:deep(.markdown-body h2) {
  font-size: 1.75em;
}
:deep(.markdown-body h3) {
  font-size: 1.5em;
}
:deep(.markdown-body h4) {
  font-size: 1.25em;
}
:deep(.markdown-body h5) {
  font-size: 1.125em;
}
:deep(.markdown-body h6) {
  font-size: 1em;
}

:deep(.markdown-body ul),
:deep(.markdown-body ol) {
  margin-bottom: 1.25em;
  padding-left: 2em;
}

:deep(.markdown-body li) {
  margin-bottom: 0.75em;
}

:deep(.markdown-body code) {
  background-color: #edf2f7; /* Tailwind's gray-200 */
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 0.9em;
}

:deep(.markdown-body pre) {
  background-color: #edf2f7; /* Tailwind's gray-200 */
  padding: 1em;
  border-radius: 5px;
  overflow-x: auto;
  font-size: 0.9em;
}

:deep(.markdown-body a) {
  color: #4299e1; /* Tailwind's blue-500 */
  text-decoration: underline;
}

:deep(.markdown-body a:hover) {
  color: #2b6cb0; /* Tailwind's blue-700 */
}

:deep(.markdown-body blockquote) {
  border-left: 4px solid #cbd5e0; /* Tailwind's gray-400 */
  padding-left: 1em;
  color: #4a5568; /* Tailwind's gray-700 */
  font-style: italic;
  margin: 1.25em 0;
}

:deep(.markdown-body table) {
  border-collapse: collapse;
  margin: 1.25em 0;
  width: 100%;
}

:deep(.markdown-body th),
:deep(.markdown-body td) {
  border: 1px solid #e2e8f0; /* Tailwind's gray-300 */
  padding: 0.5em 1em;
}

:deep(.markdown-body th) {
  background-color: #edf2f7; /* Tailwind's gray-200 */
  font-weight: 600;
}

.loading-ellipsis {
  display: flex;
  justify-content: center;
  align-items: center;
}

.loading-ellipsis span {
  width: 10px;
  height: 10px;
  margin: 0 5px;
  background-color: #a3bffa; /* Tailwind's indigo-300 */
  border-radius: 50%;
  display: inline-block;
  animation: pulse 1.4s ease-in-out infinite;
}

.loading-ellipsis span:nth-child(2) {
  animation-delay: 0.2s;
}

.loading-ellipsis span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(0.75);
    opacity: 0.5;
  }
  50% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Ensure the loading animation is visible when scrolled to the bottom */
.overflow-y-auto {
  scroll-padding-bottom: 4rem;
}
</style>
