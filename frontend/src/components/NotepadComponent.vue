<template>
  <div class="notepad-container bg-gray-100 dark:bg-gray-800">
    <div class="bg-white dark:bg-gray-700 shadow-md p-4 flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <button
          @click="togglePreview"
          class="px-4 py-2 rounded-md text-sm font-medium transition-colors duration-200 ease-in-out"
          :class="[
            showPreview
              ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-200'
              : 'bg-gray-200 text-gray-700 dark:bg-gray-600 dark:text-gray-200',
            'hover:bg-indigo-200 dark:hover:bg-indigo-800'
          ]"
        >
          <template v-if="showPreview"> <i class="fas fa-columns mr-2"></i> Split View </template>
          <template v-else> <i class="fas fa-edit mr-2"></i> Edit Only </template>
        </button>
        <button
          @click="toggleDarkMode"
          class="p-2 rounded-md text-sm font-medium bg-gray-200 text-gray-700 dark:bg-gray-600 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-500 transition-colors duration-200 ease-in-out"
        >
          <i :class="['fas', isDarkMode ? 'fa-sun' : 'fa-moon']"></i>
        </button>
      </div>
      <div class="text-sm text-gray-500 dark:text-gray-400">
        <i class="fas fa-save mr-2"></i> Auto-saving
      </div>
    </div>
    <div
      :class="[
        'editor-container',
        { 'split-view': showPreview },
        'transition-all duration-300 ease-in-out'
      ]"
    >
      <div class="editor-wrapper">
        <textarea ref="editor" class="notepad-editor"></textarea>
      </div>
      <div
        v-if="showPreview"
        class="preview-wrapper bg-white dark:bg-gray-700 border-l border-gray-200 dark:border-gray-600"
      >
        <div class="markdown-preview" v-html="renderedMarkdown"></div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, onMounted, ref, watch, computed } from 'vue'
import CodeMirror from 'codemirror'
import 'codemirror/lib/codemirror.css'
import 'codemirror/mode/markdown/markdown.js'
import 'codemirror/addon/edit/continuelist.js'
import 'codemirror/addon/fold/foldcode.js'
import 'codemirror/addon/fold/foldgutter.js'
import 'codemirror/addon/fold/markdown-fold.js'
import 'codemirror/addon/fold/foldgutter.css'
import 'codemirror/theme/nord.css'
import api from '@/api/axios'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

import Prism from 'prismjs'
import '@/assets/prism-custom.css'
import 'prismjs/plugins/line-numbers/prism-line-numbers.js'
import 'prismjs/plugins/line-numbers/prism-line-numbers.css'

// Import languages you want to support
import 'prismjs/components/prism-python'
import 'prismjs/components/prism-c'
import 'prismjs/components/prism-javascript'
import 'prismjs/components/prism-java'
import 'prismjs/components/prism-rust'

export default defineComponent({
  name: 'NotepadComponent',
  props: {
    documentUploadId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const editor = ref<HTMLTextAreaElement | null>(null)
    let cmInstance: CodeMirror.Editor | null = null
    const showPreview = ref(true)
    const markdownContent = ref('')
    const isDarkMode = ref(false)

    const renderedMarkdown = computed(() => {
      const renderer = new marked.Renderer()
      renderer.code = (code, lang) => {
        const rawCode = typeof code === 'object' && code.raw ? code.raw : code
        // Extract the actual code content (remove backticks and language specifier)
        const codeText = rawCode.replace(/^```[\w-]*\n|```$/g, '')

        // Use the lang parameter, or try to extract it from the raw code, or default to 'plaintext'
        const language = lang || (rawCode.match(/^```([\w-]+)/) || [])[1] || 'plaintext'

        if (Prism.languages[language]) {
          const highlighted = Prism.highlight(codeText, Prism.languages[language], language)
          return `<pre class="line-numbers language-${language}"><code class="language-${language}">${highlighted}</code></pre>`
        }
        return `<pre class="line-numbers"><code>${codeText}</code></pre>`
      }

      marked.setOptions({ renderer })

      const rawHtml = marked(markdownContent.value)
      const cleanHtml = DOMPurify.sanitize(rawHtml)

      // We need to run Prism again after the content is inserted into the DOM
      setTimeout(() => {
        Prism.highlightAll()
      }, 0)

      return cleanHtml
    })

    const initializeEditor = () => {
      if (editor.value) {
        cmInstance = CodeMirror.fromTextArea(editor.value, {
          mode: 'markdown',
          theme: isDarkMode.value ? 'nord' : 'default',
          lineNumbers: true,
          lineWrapping: true,
          foldGutter: true,
          gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter'],
          extraKeys: {
            Enter: 'newlineAndIndentContinueMarkdownList',
            'Ctrl-S': saveNote,
            'Cmd-S': saveNote
          }
        })

        loadNote()

        cmInstance.on('change', () => {
          const content = cmInstance!.getValue()
          markdownContent.value = content
          debounce(saveNote, 1000)()
        })
      }
    }

    const loadNote = async () => {
      try {
        const response = await api.get(`/document-uploads/${props.documentUploadId}/note`)
        console.log('response: ', response)
        console.log('Cm Instance?: ', cmInstance)
        if (cmInstance) {
          const content = response.data.content || ''
          cmInstance.setValue(content)
          markdownContent.value = content
        }
      } catch (error) {
        console.error('Error loading note:', error)
      }
    }

    const saveNote = async () => {
      if (cmInstance) {
        try {
          const content = cmInstance.getValue()
          await api.put(`/document-uploads/${props.documentUploadId}/note`, { content })
        } catch (error) {
          console.error('Error saving note:', error)
        }
      }
    }

    const togglePreview = () => {
      showPreview.value = !showPreview.value
    }

    const toggleDarkMode = () => {
      isDarkMode.value = !isDarkMode.value
      if (cmInstance) {
        cmInstance.setOption('theme', isDarkMode.value ? 'nord' : 'default')
      }
    }

    const debounce = (func: Function, wait: number) => {
      let timeout: NodeJS.Timeout
      return (...args: any[]) => {
        clearTimeout(timeout)
        timeout = setTimeout(() => func.apply(this, args), wait)
      }
    }

    onMounted(() => {
      initializeEditor()
    })

    watch(
      () => props.documentUploadId,
      () => {
        if (cmInstance) {
          loadNote()
        }
      }
    )

    watch(isDarkMode, () => {
      if (cmInstance) {
        cmInstance.setOption('theme', isDarkMode.value ? 'nord' : 'default')
      }
    })

    return { editor, showPreview, togglePreview, renderedMarkdown, isDarkMode, toggleDarkMode }
  }
})
</script>

<style scoped>
.notepad-container {
  @apply h-full flex flex-col;
}

.editor-container {
  @apply flex-1 flex overflow-hidden;
}

.editor-wrapper,
.preview-wrapper {
  @apply flex-1 overflow-auto;
}

.split-view .editor-wrapper,
.split-view .preview-wrapper {
  @apply flex-1;
}

.notepad-editor {
  @apply w-full h-full font-mono;
}

:deep(.CodeMirror) {
  @apply h-full font-mono text-base leading-relaxed;
}

.markdown-preview {
  @apply p-6;
}

/* Headings */
.markdown-preview :deep(h1) {
  @apply text-2xl font-bold mt-6 mb-4;
}

.markdown-preview :deep(h2) {
  @apply text-xl font-bold mt-5 mb-3;
}

.markdown-preview :deep(h3) {
  @apply text-lg font-bold mt-4 mb-2;
}

/* Paragraphs and Lists */
.markdown-preview :deep(p) {
  @apply mb-4;
}

.markdown-preview :deep(ul),
.markdown-preview :deep(ol) {
  @apply mb-4 pl-8;
}

.markdown-preview :deep(li) {
  @apply mb-2;
}

/* Blockquotes */
.markdown-preview :deep(blockquote) {
  @apply border-l-4 border-gray-300 dark:border-gray-600 pl-4 italic my-4;
}

/* Code block styling */
.markdown-preview :deep(pre[class*='language-']) {
  @apply rounded-lg my-6 p-4 bg-gray-800 text-gray-100;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.markdown-preview :deep(code[class*='language-']) {
  @apply text-sm font-mono;
  text-shadow: none;
}

/* Line numbers styling */
.markdown-preview :deep(.line-numbers) {
  @apply pl-8 relative;
}

.markdown-preview :deep(.line-numbers .line-numbers-rows) {
  @apply absolute left-0 top-0 border-r border-gray-600 pl-3 pr-2 text-gray-500;
  width: auto;
}

.markdown-preview :deep(.line-numbers-rows > span:before) {
  @apply text-gray-500;
}

/* Token coloring */
.markdown-preview :deep(.token.comment),
.markdown-preview :deep(.token.prolog),
.markdown-preview :deep(.token.doctype),
.markdown-preview :deep(.token.cdata) {
  @apply text-gray-500;
}

.markdown-preview :deep(.token.punctuation) {
  @apply text-gray-300;
}

.markdown-preview :deep(.token.property),
.markdown-preview :deep(.token.tag),
.markdown-preview :deep(.token.boolean),
.markdown-preview :deep(.token.number),
.markdown-preview :deep(.token.constant),
.markdown-preview :deep(.token.symbol),
.markdown-preview :deep(.token.deleted) {
  @apply text-red-400;
}

.markdown-preview :deep(.token.selector),
.markdown-preview :deep(.token.attr-name),
.markdown-preview :deep(.token.string),
.markdown-preview :deep(.token.char),
.markdown-preview :deep(.token.builtin),
.markdown-preview :deep(.token.inserted) {
  @apply text-green-400;
}

.markdown-preview :deep(.token.operator),
.markdown-preview :deep(.token.entity),
.markdown-preview :deep(.token.url),
.markdown-preview :deep(.language-css .token.string),
.markdown-preview :deep(.style .token.string) {
  @apply text-yellow-300;
}

.markdown-preview :deep(.token.atrule),
.markdown-preview :deep(.token.attr-value),
.markdown-preview :deep(.token.keyword) {
  @apply text-blue-400;
}

.markdown-preview :deep(.token.function),
.markdown-preview :deep(.token.class-name) {
  @apply text-purple-400;
}

.markdown-preview :deep(.token.regex),
.markdown-preview :deep(.token.important),
.markdown-preview :deep(.token.variable) {
  @apply text-yellow-200;
}

/* Inline code styling */
.markdown-preview :deep(:not(pre) > code) {
  @apply bg-gray-200 dark:bg-gray-700 rounded px-1 py-0.5 font-mono text-sm text-red-600 dark:text-red-400;
}

/* Scrollbar styling for code blocks */
.markdown-preview :deep(pre[class*='language-']) {
  @apply overflow-auto;
  scrollbar-width: thin;
  scrollbar-color: #4a5568 #2d3748;
}

.markdown-preview :deep(pre[class*='language-']::-webkit-scrollbar) {
  @apply w-2 h-2;
}

.markdown-preview :deep(pre[class*='language-']::-webkit-scrollbar-track) {
  @apply bg-gray-700 rounded-b;
}

.markdown-preview :deep(pre[class*='language-']::-webkit-scrollbar-thumb) {
  @apply bg-gray-600 rounded-full border-2 border-gray-700;
}

/* Dark mode adjustments */
.dark .markdown-preview :deep(pre[class*='language-']) {
  @apply bg-gray-900 text-gray-100;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.2),
    0 2px 4px -1px rgba(0, 0, 0, 0.12);
}

.dark .markdown-preview :deep(:not(pre) > code) {
  @apply bg-gray-800 text-red-400;
}

/* Dark mode styles for CodeMirror */
:deep(.cm-s-nord.CodeMirror) {
  @apply bg-gray-900 text-gray-100;
}

:deep(.cm-s-nord .CodeMirror-gutters) {
  @apply bg-gray-900 border-r border-gray-700;
}

:deep(.cm-s-nord .CodeMirror-linenumber) {
  @apply text-gray-600;
}
.markdown-preview :deep(pre[class*='language-']) {
  @apply rounded-lg my-6 p-4 bg-gray-800 text-gray-100 relative;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.markdown-preview :deep(code[class*='language-']) {
  @apply text-sm font-mono;
  text-shadow: none;
}

/* Line numbers styling */
.markdown-preview :deep(.line-numbers) {
  @apply pl-12 relative; /* Increased left padding */
}

.markdown-preview :deep(.line-numbers .line-numbers-rows) {
  @apply absolute left-0 top-0 border-r border-gray-600 w-10 text-right pr-2 select-none;
  padding-top: 1em;
  pointer-events: none;
}

.markdown-preview :deep(.line-numbers-rows > span) {
  @apply block text-gray-500;
  counter-increment: linenumber;
}

.markdown-preview :deep(.line-numbers-rows > span::before) {
  @apply block pr-2 text-gray-500;
  content: counter(linenumber);
}

/* Ensure code content doesn't overlap with line numbers */
.markdown-preview :deep(.line-numbers code) {
  @apply pl-4; /* Add left padding to code content */
}

.markdown-preview :deep(pre[class*='language-']) {
  @apply rounded-lg my-6 p-4 bg-gray-800 text-gray-100 relative;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.markdown-preview :deep(code[class*='language-']) {
  @apply text-sm font-mono;
  text-shadow: none;
}

/* Line numbers styling */
.markdown-preview :deep(.line-numbers) {
  @apply pl-12 relative; /* Increased left padding */
}

.markdown-preview :deep(.line-numbers .line-numbers-rows) {
  @apply absolute left-0 top-0 border-r border-gray-600 w-10 text-right pr-2 select-none;
  padding-top: 1em;
  pointer-events: none;
}

.markdown-preview :deep(.line-numbers-rows > span) {
  @apply block text-gray-500;
  counter-increment: linenumber;
}

.markdown-preview :deep(.line-numbers-rows > span::before) {
  @apply block pr-2 text-gray-500;
  content: counter(linenumber);
}

/* Ensure code content doesn't overlap with line numbers */
.markdown-preview :deep(.line-numbers code) {
  @apply pl-4; /* Add left padding to code content */
}
</style>
