<template>
  <div class="website-viewer">
    <iframe
      :src="contentUrl"
      class="w-full h-[calc(100vh-200px)]"
      sandbox="allow-scripts allow-same-origin"
      referrerpolicy="no-referrer"
    ></iframe>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'WebsiteViewer',
  props: {
    contentUrl: {
      type: String,
      required: true
    }
  },
  setup() {
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
