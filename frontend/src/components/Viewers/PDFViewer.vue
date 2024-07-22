<template>
  <div class="pdf-viewer">
    <div v-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="!pdfUrl" class="loading-message">Waiting for PDF...</div>
    <vue-pdf-embed v-else text-layer annotation-layer :source="pdfUrl" />
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, watch } from 'vue'
import VuePdfEmbed from 'vue-pdf-embed'
import 'vue-pdf-embed/dist/style/index.css'
import 'vue-pdf-embed/dist/style/textLayer.css'
import 'vue-pdf-embed/dist/style/annotationLayer.css'

export default defineComponent({
  name: 'PDFViewer',
  components: { VuePdfEmbed },
  props: {
    pdfUrl: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const error = ref<string | null>(null)

    watch(
      () => props.pdfUrl,
      (newUrl) => {
        console.log('PDF URL changed:', newUrl)
        error.value = null
      }
    )

    return { error }
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
