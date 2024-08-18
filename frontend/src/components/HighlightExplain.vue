<template>
  <div
    class="bg-gradient-to-br from-blue-50 to-indigo-100 p-8 shadow-lg rounded-xl border border-blue-200"
  >
    <h3 class="text-3xl font-extrabold mb-6 text-indigo-800 tracking-tight">
      Highlight and Explain
    </h3>

    <!-- Text Input -->
    <div class="mb-6">
      <label for="highlight-input" class="block text-sm font-medium text-gray-700 mb-2"
        >Enter text to highlight and explain</label
      >
      <textarea
        id="highlight-input"
        v-model="highlightText"
        rows="4"
        class="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        placeholder="Enter text from the document here..."
      ></textarea>
    </div>

    <!-- Action Button -->
    <button
      @click="explainHighlight"
      class="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-6 py-3 rounded-lg font-bold text-lg transition duration-300 ease-in-out transform hover:from-blue-600 hover:to-indigo-700 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 shadow-md"
    >
      Explain Highlighted Text
    </button>

    <!-- Explanation Area -->
    <div
      v-if="explanation"
      class="mt-6 bg-white p-6 rounded-lg shadow-inner border border-blue-100"
    >
      <h4 class="font-semibold text-xl mb-4 text-indigo-700">Explanation:</h4>
      <p class="text-gray-700 leading-relaxed">{{ explanation }}</p>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref } from 'vue'

export default defineComponent({
  name: 'HighlightExplain',
  props: {
    documentUploadId: {
      type: String,
      required: true
    }
  },
  setup() {
    const highlightText = ref('')
    const explanation = ref('')

    const explainHighlight = () => {
      if (highlightText.value.trim()) {
        // Simulating explanation generation
        explanation.value = `This is a dummy explanation for the highlighted text: "${highlightText.value}". In a real implementation, this would provide context and insights about the selected text based on the document content.`
      }
    }

    return {
      highlightText,
      explanation,
      explainHighlight
    }
  }
})
</script>
