<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'
import NavBar from '@/components/NavBar.vue'
import { computed } from 'vue'

const route = useRoute()

const showNavBar = computed(() => {
  // Add routes where you don't want to show the navbar
  const routesWithoutNavBar = ['/auth']
  return !routesWithoutNavBar.includes(route.path)
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-indigo-50 to-blue-100">
    <NavBar v-if="showNavBar" />
    <div :class="{ 'pt-20': showNavBar }">
      <!-- Increased padding-top from pt-16 to pt-20 -->
      <RouterView />
    </div>
  </div>
</template>
