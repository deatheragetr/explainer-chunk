// src/store/document.ts
import { defineStore } from 'pinia'
import api from '@/api/axios'

export interface OutlineItem {
  id: string
  type: string
  text: string
  level?: number
  page_number: number
  parent_id: string | null
}

interface DocumentState {
  currentDocumentId: string | null
  outline: OutlineItem[]
  currentPage: number
  isLoading: boolean
  error: string | null
  isInternalUpdate: boolean
}

export const useDocumentStore = defineStore('document', {
  state: (): DocumentState => ({
    currentDocumentId: null,
    outline: [],
    currentPage: 1,
    isLoading: false,
    error: null,
    isInternalUpdate: false // Add this flag to prevent circular updates
  }),

  actions: {
    async fetchDocumentDetails(documentId: string) {
      if (!documentId) return

      this.isLoading = true
      this.error = null

      try {
        const response = await api.get(`/document-uploads/${documentId}`)

        // Store the document ID
        this.currentDocumentId = documentId

        // Check if outline data exists
        if (
          response.data &&
          response.data.docling_structured_data &&
          response.data.docling_structured_data.outline
        ) {
          this.outline = response.data.docling_structured_data.outline
        } else {
          this.outline = []
        }

        return response.data
      } catch (error: any) {
        this.error = error.message || 'Failed to fetch document details'
        console.error('Error fetching document details:', error)
        throw error
      } finally {
        this.isLoading = false
      }
    },

    setCurrentPage(pageNumber: number, dispatchEvent = true) {
      // Prevent setting the same page (avoids unnecessary updates)
      if (this.currentPage === pageNumber) return

      // Set internal update flag to prevent circular updates
      this.isInternalUpdate = true
      this.currentPage = pageNumber

      // Only dispatch event if requested
      if (dispatchEvent) {
        // Create a custom event to notify the PDF viewer to navigate to this page
        const event = new CustomEvent('navigate-to-page', {
          detail: { pageNumber }
        })
        window.dispatchEvent(event)
      }

      // Reset the flag after a short delay
      setTimeout(() => {
        this.isInternalUpdate = false
      }, 50)
    },

    clearDocumentData() {
      this.currentDocumentId = null
      this.outline = []
      this.currentPage = 1
    }
  }
})
