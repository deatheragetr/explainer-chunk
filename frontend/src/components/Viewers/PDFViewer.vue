<!-- src/components/Viewers/PDFViewer.vue -->
<template>
  <div class="pdf-viewer" ref="pdfContainer">
    <div v-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="!contentUrl" class="loading-message">Waiting for PDF...</div>
    <div v-else>
      <!-- PDF Controls -->
      <div class="controls bg-white p-2 border-b flex items-center justify-between">
        <button
          @click="prevPage"
          class="px-3 py-1 bg-indigo-100 hover:bg-indigo-200 rounded text-indigo-800 disabled:opacity-50"
          :disabled="currentPage <= 1"
        >
          Previous
        </button>
        <span class="text-sm"> Page {{ currentPage }} of {{ totalPages }} </span>
        <button
          @click="nextPage"
          class="px-3 py-1 bg-indigo-100 hover:bg-indigo-200 rounded text-indigo-800 disabled:opacity-50"
          :disabled="currentPage >= totalPages"
        >
          Next
        </button>
      </div>

      <!-- PDF Viewer with scrollable container -->
      <div class="pdf-content" ref="pdfContent" @scroll="handleScroll">
        <vue-pdf-embed
          ref="pdfEmbed"
          text-layer
          annotation-layer
          :source="contentUrl"
          :width="containerWidth"
          :page="null"
          @loaded="onPdfLoaded"
        />
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, watch, onMounted, onUnmounted } from 'vue'
import VuePdfEmbed from 'vue-pdf-embed'
import 'vue-pdf-embed/dist/style/index.css'
import 'vue-pdf-embed/dist/style/textLayer.css'
import 'vue-pdf-embed/dist/style/annotationLayer.css'
import { useDocumentStore } from '@/store/document'

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
    const pdfContent = ref<HTMLElement | null>(null)
    const pdfEmbed = ref<any>(null)
    const containerWidth = ref<number>(0)
    const documentStore = useDocumentStore()

    const currentPage = ref<number>(1)
    const totalPages = ref<number>(1)
    const pdfLoaded = ref<boolean>(false)

    const updateContainerWidth = () => {
      if (pdfContainer.value) {
        containerWidth.value = pdfContainer.value.clientWidth
      }
    }

    const debouncedUpdateContainerWidth = debounce(updateContainerWidth, 100)

    // Scroll to a specific page using nth-child selector
    const scrollToPage = (pageNumber: number) => {
      if (!pdfContent.value || !pdfLoaded.value) {
        console.log('PDF content not ready yet')
        return
      }

      // Target the nth page element using the class you identified
      const targetPage = pdfContent.value.querySelector(
        `.vue-pdf-embed__page:nth-child(${pageNumber})`
      )

      if (targetPage) {
        // Scroll the target page into view
        targetPage.scrollIntoView({ behavior: 'smooth' })
        console.log(`Scrolled to page ${pageNumber}`)
      } else {
        console.warn(`Could not find page ${pageNumber} element`)

        // Fallback: try to find all page elements and use index
        const allPages = pdfContent.value.querySelectorAll('.vue-pdf-embed__page')
        if (allPages && allPages.length >= pageNumber) {
          // Arrays are 0-indexed, so subtract 1
          const page = allPages[pageNumber - 1]
          page.scrollIntoView({ behavior: 'smooth' })
          console.log(`Scrolled to page ${pageNumber} using array index`)
        } else {
          console.error(
            `No page elements found or page ${pageNumber} out of range (found ${allPages.length} pages)`
          )
        }
      }
    }

    const prevPage = () => {
      if (currentPage.value > 1) {
        currentPage.value -= 1
        scrollToPage(currentPage.value)
        documentStore.setCurrentPage(currentPage.value, false)
      }
    }

    const nextPage = () => {
      if (currentPage.value < totalPages.value) {
        currentPage.value += 1
        scrollToPage(currentPage.value)
        documentStore.setCurrentPage(currentPage.value, false)
      }
    }

    // Handle scroll events to update current page
    const handleScroll = debounce(() => {
      if (!pdfContent.value || !pdfLoaded.value) return

      const container = pdfContent.value
      const pages = container.querySelectorAll('.vue-pdf-embed__page')

      if (!pages || pages.length === 0) return

      const containerRect = container.getBoundingClientRect()
      const containerTop = containerRect.top
      const containerHeight = containerRect.height

      let bestVisiblePage = 1
      let maxVisibleArea = 0

      // Find which page is most visible in the viewport
      pages.forEach((page, index) => {
        const pageRect = page.getBoundingClientRect()
        const pageNum = index + 1 // Convert to 1-based index

        // Calculate how much of the page is visible
        const visibleTop = Math.max(pageRect.top, containerTop)
        const visibleBottom = Math.min(pageRect.bottom, containerTop + containerHeight)
        const visibleHeight = Math.max(0, visibleBottom - visibleTop)
        const visibleArea = visibleHeight * pageRect.width

        if (visibleArea > maxVisibleArea) {
          maxVisibleArea = visibleArea
          bestVisiblePage = pageNum
        }
      })

      if (bestVisiblePage !== currentPage.value) {
        currentPage.value = bestVisiblePage
        documentStore.setCurrentPage(bestVisiblePage, false)
      }
    }, 200)

    const onPdfLoaded = async (pdf: any) => {
      totalPages.value = pdf.numPages

      // Wait for the PDF to render all pages
      setTimeout(() => {
        pdfLoaded.value = true
        console.log('PDF pages rendered, navigation ready')

        // Set initial page from document store if available
        if (documentStore.currentPage > 0 && documentStore.currentPage <= pdf.numPages) {
          currentPage.value = documentStore.currentPage
          // Delay scrolling to ensure elements are rendered
          setTimeout(() => {
            scrollToPage(currentPage.value)
          }, 200)
        } else {
          documentStore.setCurrentPage(currentPage.value, false)
        }
      }, 1000) // Allow time for PDF to render all pages
    }

    watch(
      () => props.contentUrl,
      (newContentUrl) => {
        console.log('PDF contentUrl changed:', newContentUrl)
        error.value = null
        currentPage.value = 1
        totalPages.value = 1
        pdfLoaded.value = false
      }
    )

    // Watch for changes in the document store's current page
    watch(
      () => documentStore.currentPage,
      (newPage) => {
        if (newPage > 0 && newPage <= totalPages.value && !documentStore.isInternalUpdate) {
          if (currentPage.value !== newPage) {
            currentPage.value = newPage
            if (pdfLoaded.value) {
              scrollToPage(newPage)
            }
          }
        }
      }
    )

    onMounted(() => {
      updateContainerWidth()
      const resizeObserver = new ResizeObserver(debouncedUpdateContainerWidth)
      if (pdfContainer.value) {
        resizeObserver.observe(pdfContainer.value)
      }

      // Listen for keyboard navigation
      const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
          prevPage()
        } else if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
          nextPage()
        }
      }

      window.addEventListener('keydown', handleKeyDown)

      // Listen for navigate-to-page events
      const handleNavigateToPage = (event: CustomEvent) => {
        const { pageNumber } = event.detail
        if (pageNumber > 0 && pageNumber <= totalPages.value) {
          currentPage.value = pageNumber
          scrollToPage(pageNumber)
        }
      }

      window.addEventListener('navigate-to-page', handleNavigateToPage as EventListener)

      onUnmounted(() => {
        // Clean up listeners
        resizeObserver.disconnect()
        window.removeEventListener('keydown', handleKeyDown)
        window.removeEventListener('navigate-to-page', handleNavigateToPage as EventListener)
      })
    })

    return {
      error,
      pdfContainer,
      pdfContent,
      pdfEmbed,
      containerWidth,
      currentPage,
      totalPages,
      prevPage,
      nextPage,
      onPdfLoaded,
      handleScroll
    }
  }
})
</script>

<style scoped>
.pdf-viewer {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
}
.controls {
  position: sticky;
  top: 0;
  z-index: 10;
}
.pdf-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
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
