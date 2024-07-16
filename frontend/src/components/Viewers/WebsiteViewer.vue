<template>
    <div class="website-viewer">
      <iframe 
        :src="websiteUrl" 
        class="w-full h-[calc(100vh-200px)]"
        sandbox="allow-scripts allow-same-origin"
        referrerpolicy="no-referrer"
      ></iframe>
    </div>
  </template>
  
  <script lang="ts">
  import { defineComponent } from 'vue';
  
  export default defineComponent({
    name: 'WebsiteViewer',
    props: {
      websiteUrl: {
        type: String,
        required: true
      }
    },
    setup(props) {
      // Any additional setup logic can go here
      return {};
    }
  });
  </script>
  
  <style scoped>
  .website-viewer {
    width: 100%;
    height: 100%;
  }
  </style>