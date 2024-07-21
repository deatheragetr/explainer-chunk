<template>
  <div class="epub-viewer">
    <div id="epub-viewer-container"></div>
    <div class="controls mt-4">
      <button @click="prevPage" class="bg-blue-500 text-white px-4 py-2 rounded mr-2">
        Previous
      </button>
      <button @click="nextPage" class="bg-blue-500 text-white px-4 py-2 rounded">Next</button>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, onMounted, ref, watch } from 'vue'
import ePub from 'epubjs'

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

    const loadEpub = async () => {
      console.log('Loading epub...', props.epubUrl)
      try {
        if (props.epubUrl) {
          book.value = ePub(props.epubUrl, { openAs: 'epub' })
          rendition.value = book.value.renderTo('epub-viewer-container', {
            width: '100%',
            height: '600px',
            spread: 'always'
            // spread: 'none'
          })

          // const spine = book.value.spine
          // console.log('Spine fetched, items:', spine.items.length)

          console.log('Displaying epub...', rendition.value)
          await Promise.race([
            rendition.value.display(),
            // rendition.value.display(spine.items[0].href),
            new Promise((_, reject) =>
              setTimeout(() => reject(new Error('Rendition display timed out')), 10000)
            )
          ])

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

    onMounted(() => {
      loadEpub()
    })

    watch(
      () => props.epubUrl,
      () => {
        loadEpub()
      }
    )

    return {
      prevPage,
      nextPage
    }
  }
})
</script>

<style scoped>
.epub-viewer {
  width: 100%;
  height: 100%;
}

#epub-viewer-container {
  width: 100%;
  height: 600px;
  margin-bottom: 1rem;
  border: 1px solid #ccc;
}

.controls {
  display: flex;
  justify-content: center;
}

button {
  margin: 0 0.5rem;
}
</style>
