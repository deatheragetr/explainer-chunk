<template>
  <div class="markdown-viewer">
    <div v-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="!renderedContent" class="loading-message">Loading content...</div>
    <div v-else v-html="renderedContent" class="markdown-viewer-component-content"></div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

export default defineComponent({
  name: 'MarkdownViewer',
  props: {
    contentUrl: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const markdownContent = ref<string | null>(null)
    const error = ref<string | null>(null)
    const renderedContent = ref<string>('')

    const renderMarkdown = async (content: string): Promise<string> => {
      try {
        const rawHtml = await marked(content)
        return DOMPurify.sanitize(rawHtml)
      } catch (err) {
        console.warn('Failed to parse as Markdown, rendering as plain text:', err)
        return DOMPurify.sanitize(content.replace(/\n/g, '<br>'))
      }
    }

    watch(
      () => markdownContent.value,
      async (newContent) => {
        if (newContent) {
          renderedContent.value = await renderMarkdown(newContent)
        } else {
          renderedContent.value = ''
        }
      }
    )

    const loadMarkdown = async (url: string) => {
      try {
        const response = await fetch(url)
        markdownContent.value = await response.text()
        error.value = null
      } catch (err) {
        console.error('Error loading content:', err)
        error.value = `Error loading content: ${err instanceof Error ? err.message : String(err)}`
        markdownContent.value = null
      }
    }

    watch(
      () => props.contentUrl,
      (newUrl) => {
        if (newUrl) {
          loadMarkdown(newUrl)
        }
      },
      { immediate: true }
    )

    return { error, renderedContent }
  }
})
</script>

<style>
.markdown-viewer {
  height: 100%;
  overflow: auto;
  padding: 1rem;
  color: #24292e;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif,
    'Apple Color Emoji', 'Segoe UI Emoji';
  font-size: 16px;
  line-height: 1.5;
}

.markdown-viewer-component-content {
  max-width: 900px;
  margin: 0 auto;
}

.markdown-viewer-component-content h1 {
  font-size: 2em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-viewer-component-content h2 {
  font-size: 1.5em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-viewer-component-content h3 {
  font-size: 1.25em;
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-viewer-component-content h4 {
  font-size: 1em;
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-viewer-component-content p {
  margin-top: 0;
  margin-bottom: 16px;
}

.markdown-viewer-component-content a {
  color: #0366d6;
  text-decoration: none;
}

.markdown-viewer-component-content a:hover {
  text-decoration: underline;
}

.markdown-viewer-component-content ul,
.markdown-viewer-component-content ol {
  padding-left: 2em;
  margin-top: 0;
  margin-bottom: 16px;
}

.markdown-viewer-component-content li {
  margin-top: 0.25em;
}

.markdown-viewer-component-content code {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(27, 31, 35, 0.05);
  border-radius: 3px;
  font-family:
    SFMono-Regular,
    Consolas,
    Liberation Mono,
    Menlo,
    monospace;
}

.markdown-viewer-component-content pre {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: #f6f8fa;
  border-radius: 3px;
}

.markdown-viewer-component-content pre code {
  display: inline;
  max-width: auto;
  padding: 0;
  margin: 0;
  overflow: visible;
  line-height: inherit;
  word-wrap: normal;
  background-color: transparent;
  border: 0;
}

.markdown-viewer-component-content blockquote {
  padding: 0 1em;
  color: #6a737d;
  border-left: 0.25em solid #dfe2e5;
  margin: 0 0 16px 0;
}

.markdown-viewer-component-content table {
  display: block;
  width: 100%;
  overflow: auto;
  margin-top: 0;
  margin-bottom: 16px;
  border-spacing: 0;
  border-collapse: collapse;
}

.markdown-viewer-component-content table th {
  font-weight: 600;
}

.markdown-viewer-component-content table th,
.markdown-viewer-component-content table td {
  padding: 6px 13px;
  border: 1px solid #dfe2e5;
}

.markdown-viewer-component-content table tr {
  background-color: #fff;
  border-top: 1px solid #c6cbd1;
}

.markdown-viewer-component-content table tr:nth-child(2n) {
  background-color: #f6f8fa;
}

.markdown-viewer-component-content img {
  max-width: 100%;
  box-sizing: content-box;
  background-color: #fff;
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
