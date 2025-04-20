<!-- src/components/OutlineTree.vue -->
<script setup lang="ts">
import { computed } from 'vue'
import { useDocumentStore } from '@/store/document'

const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false
  }
})

const documentStore = useDocumentStore()

const outline = computed(() => documentStore.outline)

// Organize outline items into a hierarchical structure
const outlineTree = computed(() => {
  if (!outline.value || outline.value.length === 0) {
    return []
  }

  // Create a map of items by their ID
  const itemMap = new Map()

  // First pass: add all items to the map
  outline.value.forEach((item) => {
    itemMap.set(item.id, { ...item, children: [] })
  })

  // Second pass: build the tree structure
  const rootItems = []

  outline.value.forEach((item) => {
    const node = itemMap.get(item.id)

    if (item.parent_id === null) {
      // This is a root level item
      rootItems.push(node)
    } else if (itemMap.has(item.parent_id)) {
      // This is a child item, add it to its parent's children
      const parent = itemMap.get(item.parent_id)
      parent.children.push(node)
    } else {
      // If parent not found, add to root
      rootItems.push(node)
    }
  })

  return rootItems
})

// Function to handle clicking on an outline item
const navigateToPage = (pageNumber) => {
  documentStore.setCurrentPage(pageNumber)
}
</script>

<template>
  <div class="outline-tree">
    <h3 class="font-medium text-gray-700 mb-2 px-2" v-if="!collapsed">Document Outline</h3>
    <div v-if="outline && outline.length > 0">
      <div v-for="item in outlineTree" :key="item.id" class="mb-1">
        <div
          @click="navigateToPage(item.page_number)"
          class="flex items-center px-2 py-1 rounded hover:bg-indigo-100 cursor-pointer text-gray-700 hover:text-indigo-700 transition-colors"
          :class="{ 'justify-center': collapsed }"
        >
          <!-- Icon based on type -->
          <svg
            v-if="item.type === 'section_header'"
            class="h-4 w-4 mr-1"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
          <svg
            v-else-if="item.type === 'figure'"
            class="h-4 w-4 mr-1"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <svg
            v-else-if="item.type === 'table'"
            class="h-4 w-4 mr-1"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>

          <!-- Text (only show if not collapsed) -->
          <span v-if="!collapsed" class="truncate">
            {{ item.text.length > 50 ? item.text.substring(0, 50) + '...' : item.text }}
            <span class="text-xs text-gray-500 ml-1">(p.{{ item.page_number }})</span>
          </span>
        </div>

        <!-- Recursively render children with indent -->
        <div v-if="!collapsed && item.children && item.children.length > 0" class="pl-4">
          <div v-for="child in item.children" :key="child.id" class="mb-1">
            <div
              @click="navigateToPage(child.page_number)"
              class="flex items-center px-2 py-1 rounded hover:bg-indigo-100 cursor-pointer text-gray-700 hover:text-indigo-700 transition-colors"
            >
              <!-- Icon based on type -->
              <svg
                v-if="child.type === 'section_header'"
                class="h-4 w-4 mr-1"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
              <svg
                v-else-if="child.type === 'figure'"
                class="h-4 w-4 mr-1"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <svg
                v-else-if="child.type === 'table'"
                class="h-4 w-4 mr-1"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>

              <span class="truncate">
                {{ child.text.length > 50 ? child.text.substring(0, 50) + '...' : child.text }}
                <span class="text-xs text-gray-500 ml-1">(p.{{ child.page_number }})</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="text-gray-500 text-sm px-2">No outline available</div>
  </div>
</template>
