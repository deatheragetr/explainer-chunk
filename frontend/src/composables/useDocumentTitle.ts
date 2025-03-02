import { ref, watch } from 'vue'
import axios from 'axios'

// Create a reactive state that will be shared between components
const documentTitle = ref('')
const documentUploadId = ref<string | null>(null)
const isEditingTitle = ref(false)

// Watch for changes to documentUploadId and update the document title in the browser tab
watch(documentTitle, (newTitle) => {
  if (newTitle) {
    document.title = newTitle
  } else {
    document.title = 'ExplainerAde'
  }
})

export function useDocumentTitle() {
  const setDocumentTitle = (title: string) => {
    documentTitle.value = title
  }

  const setDocumentId = (id: string | null) => {
    documentUploadId.value = id
  }

  const resetDocument = () => {
    documentTitle.value = ''
    documentUploadId.value = null
    document.title = 'ExplainerAde'
  }

  const startEditingTitle = () => {
    isEditingTitle.value = true
  }

  const stopEditingTitle = () => {
    isEditingTitle.value = false
  }

  const saveTitle = async (newTitle: string) => {
    if (!documentUploadId.value || !newTitle.trim()) {
      isEditingTitle.value = false
      return
    }

    try {
      const response = await axios.patch(
        `http://localhost:8000/document-uploads/${documentUploadId.value}`,
        {
          custom_title: newTitle.trim()
        }
      )

      // Update the document title
      setDocumentTitle(response.data.title)
      isEditingTitle.value = false

      return response.data.title
    } catch (error) {
      console.error('Error updating document title:', error)
      isEditingTitle.value = false
      throw error
    }
  }

  return {
    documentTitle,
    documentUploadId,
    isEditingTitle,
    setDocumentTitle,
    setDocumentId,
    resetDocument,
    startEditingTitle,
    stopEditingTitle,
    saveTitle
  }
}
