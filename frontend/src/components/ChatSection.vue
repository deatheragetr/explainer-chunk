<template>
  <div
    class="bg-gradient-to-br from-blue-50 to-indigo-100 p-8 shadow-lg rounded-xl border border-blue-200"
  >
    <h3 class="text-3xl font-extrabold mb-6 text-indigo-800 tracking-tight">Chat with Document</h3>

    <!-- Chat Messages -->
    <div
      class="bg-white p-4 rounded-lg shadow-inner border border-blue-100 h-64 overflow-y-auto mb-4"
    >
      <div v-for="(message, index) in chatMessages" :key="index" class="mb-4">
        <div
          :class="[
            'p-3 rounded-lg',
            message.sender === 'user' ? 'bg-indigo-100 text-right' : 'bg-gray-100'
          ]"
        >
          <p class="font-semibold">{{ message.sender === 'user' ? 'You' : 'AI' }}</p>
          <p>{{ message.text }}</p>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="flex">
      <input
        v-model="userInput"
        @keyup.enter="sendMessage"
        type="text"
        placeholder="Type your message here..."
        class="flex-grow p-2 border border-gray-300 rounded-l-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
      />
      <button
        @click="sendMessage"
        class="bg-indigo-600 text-white px-4 py-2 rounded-r-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
      >
        Send
      </button>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref } from 'vue'

interface ChatMessage {
  sender: 'user' | 'ai'
  text: string
}

export default defineComponent({
  name: 'ChatSection',
  props: {
    documentUploadId: {
      type: String,
      required: true
    }
  },
  setup() {
    const chatMessages = ref<ChatMessage[]>([
      { sender: 'ai', text: 'Hello! How can I assist you with this document?' }
    ])
    const userInput = ref('')

    const sendMessage = () => {
      if (userInput.value.trim()) {
        chatMessages.value.push({ sender: 'user', text: userInput.value })
        // Simulating AI response
        setTimeout(() => {
          chatMessages.value.push({
            sender: 'ai',
            text: `I'm a dummy AI. You said: "${userInput.value}"`
          })
        }, 1000)
        userInput.value = ''
      }
    }

    return {
      chatMessages,
      userInput,
      sendMessage
    }
  }
})
</script>
