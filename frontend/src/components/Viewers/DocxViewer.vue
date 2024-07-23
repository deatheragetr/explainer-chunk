<template>
  <div class="docx-viewer">
    <div v-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="!content" class="loading-message">Loading document...</div>
    <div v-else class="docx-content" v-html="content"></div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, watch } from 'vue'
import mammoth from 'mammoth'

export default defineComponent({
  name: 'DocxViewer',
  props: {
    docxUrl: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const content = ref<string | null>(null)
    const error = ref<string | null>(null)

    const loadDocx = async (url: string) => {
      try {
        const response = await fetch(url)
        const arrayBuffer = await response.arrayBuffer()
        const result = await mammoth.convertToHtml({ arrayBuffer })
        content.value = result.value
        error.value = null
      } catch (err) {
        console.error('Error loading DOCX:', err)
        error.value = `Error loading DOCX: ${err instanceof Error ? err.message : String(err)}`
        content.value = null
      }
    }

    watch(
      () => props.docxUrl,
      (newUrl) => {
        if (newUrl) {
          loadDocx(newUrl)
        }
      },
      { immediate: true }
    )

    return { content, error }
  }
})
</script>

<style>
.docx-viewer {
  height: 100%;
  overflow: auto;
  padding: 1rem;
  color: #333;
  font-family: Arial, sans-serif;
  line-height: 1.6;
}

.docx-content {
  max-width: 800px;
  margin: 0 auto;
}

.docx-content h1 {
  font-size: 2.5em;
  color: #2c3e50;
  border-bottom: 2px solid #ecf0f1;
  padding-bottom: 10px;
  margin-top: 1.5em;
  margin-bottom: 0.8em;
}

.docx-content h2 {
  font-size: 2em;
  color: #34495e;
  margin-top: 1.3em;
  margin-bottom: 0.7em;
}

.docx-content h3 {
  font-size: 1.5em;
  color: #7f8c8d;
  margin-top: 1.1em;
  margin-bottom: 0.6em;
}

.docx-content h4 {
  font-size: 1.25em;
  color: #95a5a6;
  margin-top: 1em;
  margin-bottom: 0.5em;
}

.docx-content p {
  margin-bottom: 1em;
}

.docx-content ul,
.docx-content ol {
  margin-bottom: 1em;
  padding-left: 2em;
}

.docx-content li {
  margin-bottom: 0.5em;
}

.docx-content a {
  color: #3498db;
  text-decoration: none;
}

.docx-content a:hover {
  text-decoration: underline;
}

.docx-content blockquote {
  border-left: 5px solid #ecf0f1;
  padding-left: 1em;
  margin-left: 0;
  font-style: italic;
  color: #7f8c8d;
}

.docx-content code {
  background-color: #f8f8f8;
  padding: 2px 4px;
  border-radius: 4px;
  font-family: 'Courier New', Courier, monospace;
}

.docx-content pre {
  background-color: #f8f8f8;
  padding: 1em;
  border-radius: 4px;
  overflow-x: auto;
}

.docx-content table {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1em;
}

.docx-content th,
.docx-content td {
  border: 1px solid #ecf0f1;
  padding: 8px;
  text-align: left;
}

.docx-content th {
  background-color: #f2f2f2;
  font-weight: bold;
}

.docx-content img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 1em auto;
}

.error-message,
.loading-message {
  color: #666;
  text-align: center;
  padding: 1rem;
}

.error-message {
  color: #e74c3c;
}
</style>
