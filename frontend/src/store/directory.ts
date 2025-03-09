import { defineStore } from 'pinia'
import directoryService from '@/api/directoryService'
import type { Directory, DirectoryContents, DirectoryTreeNode } from '@/types/directory'
import { buildDirectoryTree, buildBreadcrumbs } from '@/types/directory'

interface DirectoryState {
  directories: Directory[]
  currentDirectory: Directory | null
  directoryContents: DirectoryContents | null
  directoryTree: DirectoryTreeNode[]
  breadcrumbs: { _id: string | null; name: string; path: string }[]
  isLoading: boolean
  error: string | null
}

export const useDirectoryStore = defineStore('directory', {
  state: (): DirectoryState => ({
    directories: [],
    currentDirectory: null,
    directoryContents: null,
    directoryTree: [],
    breadcrumbs: [{ _id: null, name: 'Home', path: '/' }],
    isLoading: false,
    error: null
  }),

  getters: {
    getCurrentDirectoryId: (state) => state.currentDirectory?._id || null,
    getCurrentDirectoryPath: (state) => state.currentDirectory?.path || '/',
    getDirectoryById: (state) => (id: string) => state.directories.find((dir) => dir._id === id),
    getDirectoryByPath: (state) => (path: string) =>
      state.directories.find((dir) => dir.path === path)
  },

  actions: {
    async fetchAllDirectories() {
      this.isLoading = true
      this.error = null
      try {
        this.directories = await directoryService.getDirectories()
        this.directoryTree = buildDirectoryTree(this.directories)
      } catch (error: any) {
        this.error = error.message || 'Failed to fetch directories'
        console.error('Error fetching directories:', error)
      } finally {
        this.isLoading = false
      }
    },

    async fetchDirectoryContents(directoryId: string | null = null) {
      this.isLoading = true
      this.error = null
      try {
        this.directoryContents = await directoryService.getDirectoryContents(directoryId)

        // If we're fetching a specific directory, set it as current
        if (directoryId) {
          const directory = this.getDirectoryById(directoryId)
          if (directory) {
            this.currentDirectory = directory
            this.breadcrumbs = buildBreadcrumbs(directory, this.directories)
          }
        } else {
          this.currentDirectory = null
          this.breadcrumbs = [{ _id: null, name: 'Home', path: '/' }]
        }
      } catch (error: any) {
        this.error = error.message || 'Failed to fetch directory contents'
        console.error('Error fetching directory contents:', error)
      } finally {
        this.isLoading = false
      }
    },

    async createDirectory(name: string, parentId: string | null = null) {
      this.isLoading = true
      this.error = null
      try {
        const newDirectory = await directoryService.createDirectory(name, parentId)
        this.directories.push(newDirectory)
        this.directoryTree = buildDirectoryTree(this.directories)

        // Refresh directory contents if we're in the parent directory
        if (
          (parentId === null && this.currentDirectory === null) ||
          (parentId !== null && this.currentDirectory?._id === parentId)
        ) {
          await this.fetchDirectoryContents(parentId)
        }

        return newDirectory
      } catch (error: any) {
        this.error = error.message || 'Failed to create directory'
        console.error('Error creating directory:', error)
        throw error
      } finally {
        this.isLoading = false
      }
    },

    async updateDirectory(directoryId: string, name: string) {
      this.isLoading = true
      this.error = null
      try {
        const updatedDirectory = await directoryService.updateDirectory(directoryId, name)

        // Update local state
        const index = this.directories.findIndex((dir) => dir._id === directoryId)
        if (index !== -1) {
          this.directories[index] = updatedDirectory
        }

        // Update current directory if it's the one being updated
        if (this.currentDirectory?._id === directoryId) {
          this.currentDirectory = updatedDirectory
          this.breadcrumbs = buildBreadcrumbs(updatedDirectory, this.directories)
        }

        this.directoryTree = buildDirectoryTree(this.directories)

        // Refresh directory contents if needed
        if (this.currentDirectory?._id === updatedDirectory.parent_id) {
          await this.fetchDirectoryContents(this.currentDirectory._id)
        }

        return updatedDirectory
      } catch (error: any) {
        this.error = error.message || 'Failed to update directory'
        console.error('Error updating directory:', error)
        throw error
      } finally {
        this.isLoading = false
      }
    },

    async deleteDirectory(directoryId: string, recursive: boolean = false) {
      this.isLoading = true
      this.error = null
      try {
        const result = await directoryService.deleteDirectory(directoryId, recursive)

        // Get parent ID before removing from local state
        const directory = this.getDirectoryById(directoryId)
        const parentId = directory?.parent_id

        // Remove from local state
        this.directories = this.directories.filter((dir) => dir._id !== directoryId)

        // If recursive, also remove all children
        if (recursive && directory) {
          this.directories = this.directories.filter(
            (dir) => !dir.path.startsWith(directory.path + '/')
          )
        }

        this.directoryTree = buildDirectoryTree(this.directories)

        // If we're in the deleted directory, navigate to parent
        if (this.currentDirectory?._id === directoryId) {
          await this.fetchDirectoryContents(parentId)
        } else if (this.currentDirectory?._id === parentId) {
          // Refresh contents if we're in the parent directory
          await this.fetchDirectoryContents(parentId)
        }

        return result
      } catch (error: any) {
        this.error = error.message || 'Failed to delete directory'
        console.error('Error deleting directory:', error)
        throw error
      } finally {
        this.isLoading = false
      }
    },

    async moveDirectory(directoryId: string, newParentId: string | null = null) {
      this.isLoading = true
      this.error = null
      try {
        const movedDirectory = await directoryService.moveDirectory(directoryId, newParentId)

        // Get old parent ID before updating local state
        const directory = this.getDirectoryById(directoryId)
        const oldParentId = directory?.parent_id

        // Update local state
        await this.fetchAllDirectories() // Refresh all directories to get updated paths

        // Refresh contents if we're in the old or new parent directory
        if (
          this.currentDirectory?._id === oldParentId ||
          this.currentDirectory?._id === newParentId
        ) {
          await this.fetchDirectoryContents(this.currentDirectory._id)
        }

        // If we're in the moved directory, update breadcrumbs
        if (this.currentDirectory?._id === directoryId) {
          const updatedDirectory = this.getDirectoryById(directoryId)
          if (updatedDirectory) {
            this.currentDirectory = updatedDirectory
            this.breadcrumbs = buildBreadcrumbs(updatedDirectory, this.directories)
          }
        }

        return movedDirectory
      } catch (error: any) {
        this.error = error.message || 'Failed to move directory'
        console.error('Error moving directory:', error)
        throw error
      } finally {
        this.isLoading = false
      }
    },

    async moveDocument(documentId: string, directoryId: string | null = null) {
      this.isLoading = true
      this.error = null
      try {
        const result = await directoryService.moveDocument(documentId, directoryId)

        // Refresh current directory contents
        if (this.currentDirectory) {
          await this.fetchDirectoryContents(this.currentDirectory._id)
        } else {
          await this.fetchDirectoryContents(null)
        }

        return result
      } catch (error: any) {
        this.error = error.message || 'Failed to move document'
        console.error('Error moving document:', error)
        throw error
      } finally {
        this.isLoading = false
      }
    },

    async navigateToDirectory(directoryId: string | null) {
      await this.fetchDirectoryContents(directoryId)
    },

    // This method is no longer needed since we're using navigateToDirectory directly
    // and not using URL paths for directory navigation
    async navigateToPath(path: string) {
      if (path === '/' || path === '') {
        return this.navigateToDirectory(null)
      }

      // For backward compatibility, just navigate to root
      return this.navigateToDirectory(null)
    }
  }
})
