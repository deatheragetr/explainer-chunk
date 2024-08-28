<template>
  <div class="json-viewer">
    <pre v-if="parsedJson" class="json-content">{{ formattedJson }}</pre>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div v-else class="loading-message">Loading JSON...</div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, watch } from 'vue'

export default defineComponent({
  name: 'JSONViewer',
  props: {
    contentUrl: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const parsedJson = ref<any>(null)
    const error = ref<string | null>(null)

    const formattedJson = computed(() => {
      return JSON.stringify(parsedJson.value, null, 2)
    })

    const loadJson = async (url: string) => {
      try {
        const response = await fetch(url)
        const json = await response.json()
        parsedJson.value = json
        error.value = null
      } catch (err) {
        console.error('Error loading JSON:', err)
        error.value = `Error loading JSON: ${err instanceof Error ? err.message : String(err)}`
        parsedJson.value = null
      }
    }

    watch(
      () => props.contentUrl,
      (newUrl) => {
        if (newUrl) {
          loadJson(newUrl)
        }
      },
      { immediate: true }
    )

    return { parsedJson, error, formattedJson }
  }
})
</script>

<style scoped>
.json-viewer {
  height: 100%;
  overflow: auto;
}
.json-content {
  white-space: pre-wrap;
  word-wrap: break-word;
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
