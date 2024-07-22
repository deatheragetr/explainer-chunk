<template>
  <div class="pdf-viewer">
    <div v-if="loading" class="loading">Loading PDF...</div>
    <div class="pdf-container" ref="pdfContainer" @scroll="handleScroll">
      <div
        class="pdf-content"
        :style="{ transform: `scale(${scale})`, transformOrigin: 'center top' }"
      >
        <div v-for="page in renderedPages" :key="page" class="page-container">
          <canvas
            :ref="
              (el) => {
                if (el) canvasRefs[page] = el
              }
            "
          ></canvas>
          <div
            class="textLayer"
            :ref="
              (el) => {
                if (el) textLayerRefs[page] = el
              }
            "
          ></div>
        </div>
      </div>
    </div>
    <div class="controls">
      <div class="control-group">
        <button
          @click="prevPage"
          :disabled="currentPage === 1"
          class="icon-button"
          aria-label="Previous page"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="icon"
          >
            <polyline points="18 15 12 9 6 15"></polyline>
          </svg>
        </button>
        <span class="page-info">Page {{ currentPage }} of {{ totalPages }}</span>
        <button
          @click="nextPage"
          :disabled="currentPage === totalPages"
          class="icon-button"
          aria-label="Next page"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="icon"
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
      </div>
      <div class="control-group">
        <button @click="zoomOut" :disabled="scale <= 0.5" class="icon-button" aria-label="Zoom out">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="icon"
          >
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
        <span class="zoom-info">{{ Math.round(scale * 100) }}%</span>
        <button @click="zoomIn" :disabled="scale >= 3" class="icon-button" aria-label="Zoom in">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="icon"
          >
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, watch, reactive, nextTick } from 'vue'
import * as pdfjsLib from 'pdfjs-dist/webpack.mjs'
import { TextLayer } from 'pdfjs-dist'

import PDFWorker from 'pdfjs-dist/build/pdf.worker.mjs?worker'
pdfjsLib.GlobalWorkerOptions.workerPort = new PDFWorker()

export default defineComponent({
  name: 'PDFViewer',
  props: {
    pdfUrl: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const pdfContainer = ref<HTMLDivElement | null>(null)
    const canvasRefs = reactive<{ [key: number]: HTMLCanvasElement }>({})
    const textLayerRefs = reactive<{ [key: number]: HTMLDivElement }>({})
    const loading = ref(true)
    const currentPage = ref(1)
    const totalPages = ref(0)
    const renderedPages = ref<number[]>([])
    let pdfDoc: any = null
    const scale = ref(1)
    const baseScale = ref(1.5)
    const renderingQueue = reactive<{ [key: number]: boolean }>({})
    let cancelRendering = false
    let scrollTimeout: number | null = null
    let isScrolling = false
    let isProgrammaticScroll = false

    const renderPage = async (pageNum: number) => {
      if (!pdfDoc || renderingQueue[pageNum]) return
      renderingQueue[pageNum] = true

      try {
        const page = await pdfDoc.getPage(pageNum)
        // const viewport = page.getViewport({ scale: scale.value })
        const viewport = page.getViewport({ scale: baseScale.value })

        const canvas = canvasRefs[pageNum]
        const textLayerDiv = textLayerRefs[pageNum]

        if (canvas && !cancelRendering) {
          const context = canvas.getContext('2d')
          canvas.height = viewport.height
          canvas.width = viewport.width

          const renderContext = {
            canvasContext: context!,
            viewport: viewport
          }

          const renderTask = page.render(renderContext)

          if (textLayerDiv && !cancelRendering) {
            textLayerDiv.innerHTML = ''
            textLayerDiv.style.width = `${viewport.width}px`
            textLayerDiv.style.height = `${viewport.height}px`

            const textContent = await page.getTextContent()
            await renderTask.promise // Wait for canvas rendering to complete

            const textLayerTask = new TextLayer({
              textContentSource: textContent,
              viewport: viewport,
              container: textLayerDiv,
              textDivs: [],
              enhanceTextSelection: true
            })
            await textLayerTask.render()
          }

          await renderTask.promise
        }
      } catch (error) {
        console.error(`Error rendering page ${pageNum}:`, error)
      } finally {
        renderingQueue[pageNum] = false
      }
    }

    const loadPDF = async () => {
      try {
        loading.value = true
        console.log('Loading PDF from URL:', props.pdfUrl)
        pdfDoc = await pdfjsLib.getDocument(props.pdfUrl).promise
        console.log('PDF loaded successfully. Number of pages:', pdfDoc.numPages)
        totalPages.value = pdfDoc.numPages
        currentPage.value = 1
        renderedPages.value = Array.from({ length: totalPages.value }, (_, i) => i + 1)
        await nextTick() // Ensure DOM is updated
        await renderVisiblePages()
      } catch (error) {
        console.error('Error loading PDF:', error)
        if (error instanceof Error) {
          console.error('Error name:', error.name)
          console.error('Error message:', error.message)
          console.error('Error stack:', error.stack)
        }
      } finally {
        loading.value = false
      }
    }

    const renderVisiblePages = async () => {
      if (!pdfContainer.value) return

      cancelRendering = true
      await new Promise((resolve) => setTimeout(resolve, 0))
      cancelRendering = false

      const { scrollTop, clientHeight } = pdfContainer.value
      const visiblePages = renderedPages.value.filter((pageNum) => {
        const canvas = canvasRefs[pageNum]
        if (!canvas) return false
        const rect = canvas.getBoundingClientRect()
        return rect.top < clientHeight * 2 && rect.bottom > -clientHeight
      })

      // Sort pages by visibility (closest to the viewport first)
      visiblePages.sort((a, b) => {
        const rectA = canvasRefs[a].getBoundingClientRect()
        const rectB = canvasRefs[b].getBoundingClientRect()
        return Math.abs(rectA.top) - Math.abs(rectB.top)
      })

      for (const pageNum of visiblePages) {
        if (!cancelRendering) {
          await renderPage(pageNum)
        }
      }
    }

    const updateCurrentPage = () => {
      if (!pdfContainer.value) return

      const { clientHeight } = pdfContainer.value

      // console.log('\n\n\nMiddle Y: ', middleY)
      // console.log('CLIENT HEIGHT: ', clientHeight)
      // console.log('Scroolltopp: ', scrollTop)

      let newCurrentPage = 1
      for (const pageNum of renderedPages.value) {
        const canvas = canvasRefs[pageNum]
        if (!canvas) continue
        const rect = canvas.getBoundingClientRect()
        // console.log('pageNumber: ', pageNum, ' Top: ', rect.top)

        // Math seems to work well-enough.
        // Basically when a page is GTE half-way up the viewport, we set current page to that page number
        // Until the top page is GT halfway past (up and out of view) the viewport
        if (rect.top <= clientHeight / 2 && rect.top > clientHeight / -2) {
          newCurrentPage = pageNum
          break
        }
      }

      if (!isProgrammaticScroll) {
        currentPage.value = newCurrentPage
      }
    }
    const handleScroll = () => {
      if (isProgrammaticScroll) return

      if (scrollTimeout) {
        clearTimeout(scrollTimeout)
      }

      if (!isScrolling) {
        isScrolling = true
      }

      scrollTimeout = setTimeout(() => {
        isScrolling = false
        updateCurrentPage()
        renderVisiblePages()
      }, 100) // Adjust this delay as needed
    }

    const scrollToPage = (pageNum: number) => {
      if (!pdfContainer.value) return

      isProgrammaticScroll = true

      let scrollTop = 0
      for (let i = 1; i < pageNum; i++) {
        const canvas = canvasRefs[i]
        if (canvas) {
          scrollTop += canvas.height + 10 // Add a small gap between pages per the configured CSS margin-bottom
        }
      }

      pdfContainer.value.scrollTop = scrollTop

      // Use requestAnimationFrame to ensure the scroll has completed
      requestAnimationFrame(() => {
        isProgrammaticScroll = false
        // updateCurrentPage()
        // renderVisiblePages()
      })
    }

    const prevPage = () => {
      if (currentPage.value > 1) {
        currentPage.value--
        scrollToPage(currentPage.value)
      }
    }

    const nextPage = () => {
      if (currentPage.value < totalPages.value) {
        currentPage.value++
        scrollToPage(currentPage.value)
      }
    }

    const zoomIn = () => {
      if (scale.value < 3) {
        scale.value += 0.25
        adjustScrollAfterZoom()
      }
    }

    const zoomOut = () => {
      if (scale.value > 0.5) {
        scale.value -= 0.25
        adjustScrollAfterZoom()
      }
    }

    const adjustScrollAfterZoom = () => {
      if (!pdfContainer.value) return
      const container = pdfContainer.value
      const scrollXCenter = container.scrollLeft + container.clientWidth / 2
      const scrollYCenter = container.scrollTop + container.clientHeight / 2
      container.scrollLeft = scrollXCenter * scale.value - container.clientWidth / 2
      container.scrollTop = scrollYCenter * scale.value - container.clientHeight / 2
    }

    onMounted(() => {
      loadPDF()
    })

    watch(
      () => props.pdfUrl,
      () => {
        loadPDF()
      }
    )

    return {
      pdfContainer,
      canvasRefs,
      textLayerRefs,
      loading,
      currentPage,
      totalPages,
      renderedPages,
      prevPage,
      nextPage,
      handleScroll,
      scale,
      zoomIn,
      zoomOut
    }
  }
})
</script>

<style scoped>
.pdf-viewer {
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  width: 100%;
}

.pdf-container {
  /* position: relative; */
  /* width: 100%; */
  /* height: calc(100% - 50px); Adjust based on your controls height */
  /* overflow-y: auto; */
  /* display: flex; */
  /* justify-content: center; */

  /* position: relative;
  width: 100%;
  height: calc(100% - 50px);
  overflow: auto; */

  position: relative;
  width: 100%;
  height: calc(100% - 60px); /* Adjusted to accommodate taller controls */
  overflow: auto;
  display: flex;
  justify-content: center;
}

.pdf-content {
  /* display: flex; */
  display: inline-block; /* Changed from flex to inline-block */
  /* min-width: 100%;
  min-height: 100%; */

  /* 
  flex-direction: column;
  align-items: center; */

  display: inline-block;
  text-align: center;
}

.page-container {
  /* position: relative;
  margin-bottom: 10px; */
  display: inline-block;
  margin-bottom: 10px;
}

.textLayer {
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
  opacity: 0.2;
  line-height: 1;
  user-select: text;
}

.textLayer > span {
  color: transparent;
  position: absolute;
  white-space: pre;
  cursor: text;
  transform-origin: 0% 0%;
}

.textLayer .highlight {
  margin: -1px;
  padding: 1px;
  background-color: rgb(180, 0, 170);
  border-radius: 4px;
}

.textLayer .highlight.selected {
  background-color: rgb(0, 100, 0);
}

.controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background-color: rgba(255, 255, 255, 0.8);
  padding: 10px;
  border-radius: 5px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.control-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-info,
.zoom-info {
  min-width: 100px;
  text-align: center;
}

canvas {
  max-width: 100%;
  height: auto;
}

.loading {
  font-size: 1.2rem;
  color: #666;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}
.controls button {
  padding: 5px 10px;
  margin: 0 5px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

.controls button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.icon-button {
  background-color: transparent;
  border: none;
  cursor: pointer;
  padding: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #007bff;
  transition: color 0.3s ease;
}

.icon-button:hover:not(:disabled) {
  color: #0056b3;
}

.icon-button:disabled {
  color: #ccc;
  cursor: not-allowed;
}

.icon {
  width: 24px;
  height: 24px;
}
</style>
