<template>
  <div class="pdf-viewer" ref="pdfContainer">
    <div v-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="!contentUrl" class="loading-message">Waiting for PDF...</div>
    <vue-pdf-embed
      v-else
      text-layer
      annotation-layer
      :source="contentUrl"
      :width="containerWidth"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, watch, onMounted, onUnmounted } from 'vue'
import VuePdfEmbed from 'vue-pdf-embed'
import 'vue-pdf-embed/dist/style/index.css'
import 'vue-pdf-embed/dist/style/textLayer.css'
import 'vue-pdf-embed/dist/style/annotationLayer.css'

// Debounce function
const debounce = (fn: Function, delay: number) => {
  let timeoutId: NodeJS.Timeout | null = null
  return (...args: any[]) => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    timeoutId = setTimeout(() => {
      fn(...args)
    }, delay)
  }
}

export default defineComponent({
  name: 'PDFViewer',
  components: { VuePdfEmbed },
  props: {
    contentUrl: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const error = ref<string | null>(null)
    const pdfContainer = ref<HTMLElement | null>(null)
    const containerWidth = ref<number>(0)

    const updateContainerWidth = () => {
      if (pdfContainer.value) {
        containerWidth.value = pdfContainer.value.clientWidth
      }
    }

    // Debounced version of updateContainerWidth
    const debouncedUpdateContainerWidth = debounce(updateContainerWidth, 100)

    watch(
      () => props.contentUrl,
      (newcontentUrl) => {
        console.log('PDF contentUrl changed:', newcontentUrl)
        error.value = null
      }
    )

    onMounted(() => {
      updateContainerWidth() // Initial width set
      const resizeObserver = new ResizeObserver(debouncedUpdateContainerWidth)
      if (pdfContainer.value) {
        resizeObserver.observe(pdfContainer.value)
      }

      onUnmounted(() => {
        resizeObserver.disconnect()
      })
    })

    return { error, pdfContainer, containerWidth }
  }
})
</script>

<style scoped>
.pdf-viewer {
  height: 100%;
  width: 100%;
}
.error-message,
.loading-message {
  color: #666;
  text-align: center;
  padding: 1rem;
}
.error-message {
  color: red;
}
</style>
