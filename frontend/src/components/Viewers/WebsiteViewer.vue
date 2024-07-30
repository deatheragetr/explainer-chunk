<template>
  <div class="website-viewer">
    <div v-if="captureStatus && captureStatus.status !== 'COMPLETE'" class="capture-status">
      <p>Capture Status: {{ captureStatus.status }}</p>
      <progress v-if="captureStatus.progress" :value="captureStatus.progress" max="100"></progress>
    </div>
    <iframe
      v-else
      :src="websiteUrl"
      class="w-full h-[calc(100vh-200px)]"
      sandbox="allow-scripts allow-same-origin"
      referrerpolicy="no-referrer"
    ></iframe>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from 'vue'

interface WebsiteCaptureStatus {
  task_id: string
  status: string
  progress: number | null
}

export default defineComponent({
  name: 'WebsiteViewer',
  props: {
    websiteUrl: {
      type: String,
      required: true
    },
    captureStatus: {
      type: Object as PropType<WebsiteCaptureStatus>,
      required: false
    }
  },
  setup(props) {
    // Any additional setup logic can go here
    return {}
  }
})
</script>

<style scoped>
.website-viewer {
  width: 100%;
  height: 100%;
}
.capture-status {
  padding: 1rem;
  background-color: #f0f0f0;
  border-radius: 4px;
  margin-bottom: 1rem;
}
</style>
