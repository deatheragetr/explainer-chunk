<template>
  <div class="inline-block animated-text">
    <span class="italic font-semibold">{{ displayedText }}</span>
    <span class="cursor" :class="{ blink: !isTyping }">|</span>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  words: string[]
  typingSpeed?: number
  deletingSpeed?: number
  pauseDuration?: number
}>()

const displayedText = ref('')
const currentWordIndex = ref(0)
const isTyping = ref(true)

let timeout: NodeJS.Timeout | null = null

const typeText = () => {
  const currentWord = props.words[currentWordIndex.value]
  if (displayedText.value.length < currentWord.length) {
    displayedText.value += currentWord[displayedText.value.length]
    timeout = setTimeout(typeText, props.typingSpeed || 100)
  } else {
    isTyping.value = false
    timeout = setTimeout(startDeleting, props.pauseDuration || 2000)
  }
}

const startDeleting = () => {
  isTyping.value = true
  deleteText()
}

const deleteText = () => {
  if (displayedText.value.length > 0) {
    displayedText.value = displayedText.value.slice(0, -1)
    timeout = setTimeout(deleteText, props.deletingSpeed || 50)
  } else {
    currentWordIndex.value = (currentWordIndex.value + 1) % props.words.length
    timeout = setTimeout(typeText, props.typingSpeed || 100)
  }
}

onMounted(() => {
  typeText()
})

onUnmounted(() => {
  if (timeout) clearTimeout(timeout)
})
</script>

<style scoped>
.animated-text {
  display: inline-block;
  min-width: 150px; /* Adjust based on your longest word */
  text-align: left;
}

.cursor {
  font-weight: 100;
  color: #2196f3;
}

.cursor.blink {
  animation: blink 0.7s infinite;
}

@keyframes blink {
  0% {
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0;
  }
}
</style>
