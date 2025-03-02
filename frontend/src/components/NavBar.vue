<template>
  <nav class="bg-white bg-opacity-90 backdrop-filter backdrop-blur-lg shadow-sm fixed w-full z-10">
    <div class="w-full px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-20">
        <div class="flex items-center">
          <router-link to="/" class="flex-shrink-0 home-link" :class="{ active: isHomePage }">
            <img class="h-10 w-auto" src="/images/logo.png" alt="Your Logo" />
          </router-link>
        </div>

        <div v-if="documentTitle" class="flex-1 flex justify-center items-center">
          <div v-if="isEditingTitle" class="flex items-center">
            <input
              ref="titleInput"
              v-model="editedTitle"
              class="block w-64 border-b border-indigo-500 focus:ring-indigo-500 focus:border-indigo-500 text-xl font-bold text-gray-900"
              @keyup.enter="handleSaveTitle"
              @keyup.esc="cancelEditTitle"
            />
            <button @click="handleSaveTitle" class="ml-2 text-indigo-600 hover:text-indigo-800">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clip-rule="evenodd"
                />
              </svg>
            </button>
            <button @click="cancelEditTitle" class="ml-1 text-gray-500 hover:text-gray-700">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clip-rule="evenodd"
                />
              </svg>
            </button>
          </div>
          <div v-else class="flex items-center group">
            <h1 class="text-xl font-bold text-gray-900 truncate">
              {{ documentTitle || 'No Document Title' }}
            </h1>
            <button
              @click="startEditTitle"
              class="ml-2 text-transparent group-hover:text-gray-400 hover:text-indigo-600"
              :disabled="!documentUploadId"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"
                />
              </svg>
            </button>
          </div>
        </div>

        <div class="hidden md:flex items-center space-x-4">
          <DocumentUploadModal @document-loaded="handleDocumentLoaded">
            <template #default="{ openModal }">
              <button
                @click="openModal"
                class="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-3 rounded-lg font-medium text-sm transition duration-300 ease-in-out transform hover:from-purple-700 hover:to-indigo-700 hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 shadow-lg"
              >
                Upload or Import
              </button>
            </template>
          </DocumentUploadModal>
          <router-link to="/settings" class="flex items-center justify-center">
            <div
              class="w-10 h-10 rounded-full bg-indigo-600 text-white flex items-center justify-center text-sm font-medium"
            >
              {{ userInitial }}
            </div>
          </router-link>
        </div>
        <div class="-mr-2 flex md:hidden">
          <!-- Mobile menu button -->
          <button
            @click="toggleMobileMenu"
            class="inline-flex items-center justify-center p-2 rounded-md text-gray-700 hover:text-indigo-600 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
          >
            <span class="sr-only">Open main menu</span>
            <!-- Icon when menu is closed -->
            <svg
              :class="{ hidden: mobileMenuOpen, block: !mobileMenuOpen }"
              class="h-6 w-6"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
            <!-- Icon when menu is open -->
            <svg
              :class="{ block: mobileMenuOpen, hidden: !mobileMenuOpen }"
              class="h-6 w-6"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Mobile menu, show/hide based on menu state -->
    <div :class="{ block: mobileMenuOpen, hidden: !mobileMenuOpen }" class="md:hidden">
      <div class="px-2 pt-2 pb-3 space-y-1 sm:px-3">
        <router-link
          to="/"
          class="text-gray-700 hover:text-indigo-600 block px-3 py-2 rounded-md text-base font-medium"
          active-class="text-indigo-600 font-semibold"
        >
          Home
        </router-link>
        <DocumentUploadModal @document-loaded="handleDocumentLoaded">
          <template #default="{ openModal }">
            <button
              @click="openModal"
              class="w-full text-left text-gray-700 hover:text-indigo-600 block px-3 py-2 rounded-md text-base font-medium"
            >
              Upload or Import
            </button>
          </template>
        </DocumentUploadModal>
        <router-link
          to="/settings"
          class="text-gray-700 hover:text-indigo-600 block px-3 py-2 rounded-md text-base font-medium"
        >
          Settings
        </router-link>
        <button
          @click="logout"
          class="text-gray-700 hover:text-indigo-600 block w-full text-left px-3 py-2 rounded-md text-base font-medium"
        >
          Logout
        </button>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { useDocumentTitle } from '@/composables/useDocumentTitle'
import DocumentUploadModal from '@/components/DocumentUploadModal.vue'

const router = useRouter()
const route = useRoute()
const { logout: authLogout, user } = useAuth()
const {
  documentTitle,
  documentUploadId,
  isEditingTitle,
  startEditingTitle,
  stopEditingTitle,
  saveTitle
} = useDocumentTitle()

const mobileMenuOpen = ref(false)
const editedTitle = ref('')
const titleInput = ref<HTMLInputElement | null>(null)

const toggleMobileMenu = () => {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

const logout = async () => {
  await authLogout()
  router.push('/login')
}

const userInitial = computed(() => {
  return user.value?.email ? user.value.email[0].toUpperCase() : 'U'
})

const isHomePage = computed(() => {
  return route.path === '/'
})

const handleDocumentLoaded = (documentData: any) => {
  console.log('Document loaded:', documentData)
  const documentUploadId = documentData.id || documentData.document_upload_id
  const newPath = `/uploads/${documentUploadId}/${documentData.url_friendly_file_name}/read`
  router.push(newPath)
}

const startEditTitle = () => {
  editedTitle.value = documentTitle.value
  startEditingTitle()
  nextTick(() => {
    if (titleInput.value) {
      titleInput.value.focus()
    }
  })
}

const cancelEditTitle = () => {
  stopEditingTitle()
}

const handleSaveTitle = async () => {
  if (!documentUploadId.value || !editedTitle.value.trim()) {
    stopEditingTitle()
    return
  }

  try {
    await saveTitle(editedTitle.value)
  } catch (error) {
    console.error('Error updating document title:', error)
    // Optionally show an error message to the user
  }
}
</script>

<style scoped>
nav {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.home-link {
  position: relative;
  transition: opacity 0.3s ease;
}

.home-link::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  width: 100%;
  height: 2px;
  background-color: #4f46e5; /* indigo-600 */
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.home-link.active::after {
  transform: scaleX(1);
}

.home-link:hover {
  opacity: 0.8;
}

@media (max-width: 768px) {
  .home-link::after {
    bottom: -2px;
  }
}
</style>
