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
      <div class="pdf-content" ref="pdfContent">
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
import { defineComponent, ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
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
    const isManualNavigation = ref<boolean>(false)

    const updateContainerWidth = () => {
      if (pdfContainer.value) {
        containerWidth.value = pdfContainer.value.clientWidth
      }
    }

    const debouncedUpdateContainerWidth = debounce(updateContainerWidth, 100)

    // Get all page elements - examining different possible selectors
    const getPageElements = () => {
      if (!pdfContent.value) return []

      console.log('Looking for page elements...')

      // Try different possible selectors for PDF pages
      const selectors = [
        '.vue-pdf-embed__page',
        '.rpv-core__viewer-page',
        '.rpv-core__page-layer',
        '.page',
        '[data-page-number]',
        'canvas'
      ]

      for (const selector of selectors) {
        const elements = pdfContent.value.querySelectorAll(selector)
        if (elements.length > 0) {
          console.log(`Found ${elements.length} elements with selector ${selector}`)
          return Array.from(elements) as HTMLElement[]
        }
      }

      // If no specific selectors work, try to find any divs with specific dimensions
      // which might be page containers
      console.log('No standard selectors found, searching for potential page containers...')
      const divs = pdfContent.value.querySelectorAll('div')
      const potentialPages = Array.from(divs).filter((div) => {
        const style = window.getComputedStyle(div)
        return parseInt(style.height) > 100 && parseInt(style.width) > 100
      })

      if (potentialPages.length > 0) {
        console.log(`Found ${potentialPages.length} potential page containers`)
        return potentialPages as HTMLElement[]
      }

      console.log('No page elements found')
      return []
    }

    // Log the DOM structure of the PDF viewer for debugging
    const logViewerStructure = () => {
      if (!pdfContent.value) return

      console.log('PDF Content Element:', pdfContent.value)

      // Find the first few levels of children
      const logChildren = (element: Element, depth = 0) => {
        if (depth > 3) return // Limit depth to avoid excessive logging

        const children = element.children
        for (let i = 0; i < children.length; i++) {
          const child = children[i]
          console.log(
            '  '.repeat(depth) +
              `Child ${i}: ${child.tagName} - Classes: ${child.className} - ID: ${child.id}`
          )
          logChildren(child, depth + 1)
        }
      }

      console.log('DOM Structure of PDF Content:')
      logChildren(pdfContent.value)
    }

    // Scroll to a specific page
    const scrollToPage = (pageNumber: number) => {
      if (!pdfContent.value || !pdfLoaded.value) {
        console.log('PDF content not ready yet')
        return
      }

      // Set flag to prevent scroll handler from immediately overriding the navigation
      isManualNavigation.value = true

      const pages = getPageElements()
      if (pages.length >= pageNumber) {
        const targetPage = pages[pageNumber - 1]
        if (targetPage) {
          targetPage.scrollIntoView({ behavior: 'smooth' })
          console.log(`Scrolled to page ${pageNumber}`)
        }
      } else {
        console.warn(`Could not find page ${pageNumber} element (found ${pages.length} pages)`)
      }

      // Reset the navigation flag after animation completes
      setTimeout(() => {
        isManualNavigation.value = false
      }, 1000)
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

    // Find the most visible page in the viewport
    const findVisiblePage = () => {
      if (!pdfContent.value) return 1

      const pages = getPageElements()
      if (!pages.length) return 1

      const scrollTop = pdfContent.value.scrollTop
      const containerHeight = pdfContent.value.clientHeight
      const containerMid = scrollTop + containerHeight / 2

      let bestVisiblePage = 1
      let closestDistance = Infinity

      pages.forEach((page, index) => {
        const rect = page.getBoundingClientRect()
        const pageTop = page.offsetTop
        const pageHeight = rect.height
        const pageMid = pageTop + pageHeight / 2
        const distance = Math.abs(pageMid - containerMid)

        if (distance < closestDistance) {
          closestDistance = distance
          bestVisiblePage = index + 1 // 1-based page numbering
        }
      })

      return bestVisiblePage
    }

    // Using a direct approach based on scroll position
    const calculatePageFromScroll = () => {
      if (!pdfContent.value || totalPages.value <= 1) return 1

      const container = pdfContent.value
      const scrollTop = container.scrollTop
      const scrollHeight = container.scrollHeight - container.clientHeight

      // If scroll not possible, we're on page 1
      if (scrollHeight <= 0) return 1

      // Calculate page based on scroll position
      const scrollRatio = scrollTop / scrollHeight
      const page = Math.floor(scrollRatio * totalPages.value) + 1

      // Make sure we're in valid range
      return Math.max(1, Math.min(page, totalPages.value))
    }

    // Handle scroll events to update current page
    const handleScroll = () => {
      console.log('Scroll event fired')

      // Skip if we're in the middle of programmatic navigation
      if (isManualNavigation.value || !pdfLoaded.value) return

      // Try both methods to find the visible page
      const visiblePage = findVisiblePage()
      const calculatedPage = calculatePageFromScroll()

      console.log(`Page detection: visiblePage=${visiblePage}, calculatedPage=${calculatedPage}`)

      // Use the visible page method if it returns something other than 1,
      // otherwise use the calculated page method
      const newPage = visiblePage !== 1 ? visiblePage : calculatedPage

      if (newPage !== currentPage.value) {
        console.log(`Updating current page to ${newPage} (was ${currentPage.value})`)
        currentPage.value = newPage
        documentStore.setCurrentPage(newPage, false)
      }
    }

    // Create debounced version for better performance
    // const debouncedHandleScroll = debounce(handleScroll, 100)
    const debouncedHandleScroll = handleScroll

    const onPdfLoaded = async (pdf: any) => {
      console.log('PDF loaded', pdf)
      totalPages.value = pdf.numPages

      // Wait for the PDF pages to render
      setTimeout(async () => {
        pdfLoaded.value = true
        console.log('PDF fully loaded, setting up scroll detection')

        // Set initial page from document store if available
        if (documentStore.currentPage > 0 && documentStore.currentPage <= pdf.numPages) {
          currentPage.value = documentStore.currentPage
        } else {
          documentStore.setCurrentPage(currentPage.value, false)
        }

        await nextTick()

        // Log the DOM structure for debugging
        logViewerStructure()

        // Add scroll listener
        if (pdfContent.value) {
          console.log('Adding scroll listener to pdfContent')
          const pdfDiv = document.getElementsByClassName('vue-pdf-embed__page')[0]
          pdfDiv.addEventListener('scroll', debouncedHandleScroll)

          // Get the page elements to make sure they're available
          const pages = getPageElements()
          console.log(`Found ${pages.length} page elements after loading`)

          // Scroll to initial page after a short delay
          setTimeout(() => {
            scrollToPage(currentPage.value)
          }, 200)
        } else {
          console.error('PDF content element not found')
        }
      }, 1000) // Allow time for PDF to render
    }

    watch(
      () => props.contentUrl,
      (newContentUrl) => {
        console.log('PDF contentUrl changed:', newContentUrl)
        error.value = null
        currentPage.value = 1
        totalPages.value = 1
        pdfLoaded.value = false

        // Remove old scroll listener when URL changes
        if (pdfContent.value) {
          pdfContent.value.removeEventListener('scroll', debouncedHandleScroll)
        }
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

        // Remove scroll listener
        if (pdfContent.value) {
          pdfContent.value.removeEventListener('scroll', debouncedHandleScroll)
        }
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
      onPdfLoaded
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
