<template>
  <div class="epub-viewer" ref="epubContainer">
    <div class="viewer-header mb-4">
      <h2 class="text-2xl font-bold">{{ bookTitle }}</h2>
      <p class="text-gray-600">{{ currentChapter }}</p>
    </div>
    <div id="epub-viewer-container" class="epub-container"></div>
    <div class="controls mt-4">
      <button @click="prevPage" class="control-btn">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          class="w-6 h-6"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 19l-7-7 7-7"
          />
        </svg>
      </button>
      <input
        type="range"
        :min="0"
        :max="100"
        v-model="progress"
        @input="handleProgressChange"
        class="w-full mx-4"
      />
      <button @click="nextPage" class="control-btn">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          class="w-6 h-6"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
    <div class="page-info mt-2 text-center">Page {{ currentPage }} of {{ totalPages }}</div>
  </div>
</template>

<script lang="ts">
import { defineComponent, onMounted, ref, watch, onBeforeUnmount, nextTick } from 'vue'
import ePub from 'epubjs'

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
  name: 'EpubViewer',
  props: {
    epubUrl: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const book = ref<ePub.Book | null>(null)
    const rendition = ref<ePub.Rendition | null>(null)
    const bookTitle = ref('')
    const currentChapter = ref('')
    const progress = ref(0)
    const currentPage = ref(1)
    const totalPages = ref(0)
    const epubContainer = ref<HTMLElement | null>(null)
    const isRenditionReady = ref(false)
    const currentWidth = ref(0)
    const currentHeight = ref(0)

    const clearViewer = () => {
      if (rendition.value) {
        rendition.value.destroy()
      }
      if (book.value) {
        book.value.destroy()
      }
      const container = document.getElementById('epub-viewer-container')
      if (container) {
        container.innerHTML = ''
      }
      isRenditionReady.value = false
    }

    const calculateTotalPages = () => {
      if (book.value && book.value.locations) {
        const totalCfi = book.value.locations.length()
        totalPages.value = Math.ceil(totalCfi / 2)
      }
    }

    const calculateViewportDimensions = () => {
      if (epubContainer.value) {
        const rect = epubContainer.value.getBoundingClientRect()
        currentWidth.value = rect.width
        // Subtracting estimated height for header, controls, and page info
        currentHeight.value = window.innerHeight - 300 // Adjust this value as needed
        // currentHeight.value = rect.height - 200
      }
    }

    const loadEpub = async () => {
      console.log('Loading epub...', props.epubUrl)
      try {
        clearViewer()

        if (props.epubUrl) {
          book.value = ePub(props.epubUrl, { openAs: 'epub' })

          await nextTick() // Wait for the DOM to update
          calculateViewportDimensions()

          rendition.value = book.value.renderTo('epub-viewer-container', {
            width: currentWidth.value,
            height: currentHeight.value,
            spread: 'always',
            minSpreadWidth: 0
          })

          book.value.loaded.metadata.then((metadata) => {
            bookTitle.value = metadata.title || 'Untitled'
          })

          book.value.loaded.navigation.then((nav) => {
            if (nav.toc[0]) {
              currentChapter.value = nav.toc[0].label
            }
          })

          rendition.value.on('rendered', () => {
            isRenditionReady.value = true
          })

          rendition.value.on('relocated', (location: any) => {
            progress.value = Math.round((location.start.percentage || 0) * 100)
            currentPage.value = Math.ceil(
              book.value!.locations.percentageFromCfi(location.start.cfi) * totalPages.value
            )

            if (book.value && book.value.navigation) {
              const chapter = book.value.navigation.get(location.start.href)
              if (chapter) {
                currentChapter.value = chapter.label
              }
            }
          })

          await rendition.value.display()

          book.value.ready.then(() => {
            book.value!.locations.generate(1024).then(() => {
              calculateTotalPages()
              console.log('Locations generated')
            })
          })

          const resizeObserver = new ResizeObserver(debouncedResizeViewer)
          if (epubContainer.value) {
            resizeObserver.observe(epubContainer.value)
          }

          console.log('EPUB loaded successfully')
        }
      } catch (e) {
        console.error('Error loading EPUB:', e)
      }
    }

    const prevPage = () => {
      rendition.value?.prev()
    }

    const nextPage = () => {
      rendition.value?.next()
    }

    const handleProgressChange = () => {
      if (book.value && rendition.value) {
        const location = book.value.locations.cfiFromPercentage(progress.value / 100)
        if (location) {
          rendition.value.display(location).catch((error) => {
            console.error('Error navigating to location:', error)
          })
        }
      }
    }

    const resizeViewer = () => {
      if (isRenditionReady.value && rendition.value && epubContainer.value) {
        calculateViewportDimensions()

        console.log(`Resizing to ${currentWidth.value}x${currentHeight.value}`)
        rendition.value.resize(currentWidth.value, currentHeight.value)
      }
    }

    const debouncedResizeViewer = debounce(resizeViewer, 200)

    onMounted(() => {
      loadEpub()
      window.addEventListener('resize', debouncedResizeViewer)

      onBeforeUnmount(() => {
        window.removeEventListener('resize', debouncedResizeViewer)
        clearViewer()
      })
    })

    watch(() => props.epubUrl, loadEpub)

    return {
      bookTitle,
      currentChapter,
      progress,
      prevPage,
      nextPage,
      currentPage,
      totalPages,
      handleProgressChange,
      epubContainer
    }
  }
})
</script>

<style scoped>
.epub-viewer {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.viewer-header {
  text-align: center;
}

.epub-container {
  flex-grow: 1;
  overflow: hidden;
}

.controls {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1rem;
}

.control-btn {
  background-color: #4a5568;
  color: white;
  padding: 0.5rem;
  border-radius: 9999px;
  transition: background-color 0.2s;
}

.control-btn:hover {
  background-color: #2d3748;
}

input[type='range'] {
  -webkit-appearance: none;
  width: 100%;
  height: 5px;
  border-radius: 5px;
  background: #e2e8f0;
  outline: none;
  opacity: 0.7;
  transition: opacity 0.2s;
}

input[type='range']:hover {
  opacity: 1;
}

input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: #4a5568;
  cursor: pointer;
}

input[type='range']::-moz-range-thumb {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: #4a5568;
  cursor: pointer;
}

.page-info {
  font-size: 0.875rem;
  color: #4a5568;
  margin-top: 0.5rem;
}
</style>
