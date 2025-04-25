import { defineStore } from 'pinia'
import directoryService from '@/api/directoryService'
import type { Directory, DirectoryContents, DirectoryTreeNode } from '@/types/directory'
import { buildDirectoryTree, buildBreadcrumbs } from '@/types/directory'
import router from '@/router'

interface DirectoryState {
  directories: Directory[]
  currentDirectory: Directory | null
  directoryContents: DirectoryContents | null
  directoryTree: DirectoryTreeNode[]
  breadcrumbs: { _id: string | null; name: string; path: string }[]
  isLoading: boolean
  error: string | null
  isNavigating: boolean
  routeInitialized: boolean
}

export const useDirectoryStore = defineStore('directory', {
  state: (): DirectoryState => ({
    directories: [],
    currentDirectory: null,
    directoryContents: null,
    directoryTree: [],
    breadcrumbs: [{ _id: null, name: 'Home', path: '/' }],
    isLoading: false,
    error: null,
    isNavigating: false,
    routeInitialized: false
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
        // Get all root directories
        const rootDirectories = await directoryService.getDirectories(null)

        if (!Array.isArray(rootDirectories)) {
          console.error('Expected rootDirectories to be an array, got:', rootDirectories)
          this.directories = []
          this.directoryTree = []
          return
        }

        // Use a Map to ensure directories are unique by ID
        const directoryMap = new Map<string, Directory>()

        // Add root directories to the map
        for (const dir of rootDirectories) {
          if (dir._id) {
            directoryMap.set(dir._id, dir)
          }
        }

        // Instead of recursion, we'll use a queue-based approach
        const directoryQueue = [...rootDirectories]
        const processedIds = new Set(rootDirectories.map((dir) => dir._id))

        // Process each directory in the queue
        while (directoryQueue.length > 0) {
          const currentDir = directoryQueue.shift()
          if (!currentDir) continue

          // Get children of this directory
          const children = await directoryService.getDirectories(currentDir._id)

          if (!Array.isArray(children)) {
            console.error(`Expected children to be an array, got:`, children)
            continue
          }

          // Add new children to our map and queue
          for (const child of children) {
            if (child._id && !processedIds.has(child._id)) {
              directoryMap.set(child._id, child)
              directoryQueue.push(child)
              processedIds.add(child._id)
            }
          }
        }

        // Convert map to array for state
        this.directories = Array.from(directoryMap.values())

        // Build the directory tree
        this.directoryTree = buildDirectoryTree(this.directories)

        // Log the number of directories for debugging
        console.log(`Fetched ${this.directories.length} unique directories`)
      } catch (error: any) {
        this.error = error.message || 'Failed to fetch directories'
        console.error('Error fetching directories:', error)
        this.directories = []
        this.directoryTree = []
      } finally {
        this.isLoading = false
      }
    },

    async fetchDirectoryContents(directoryId: string | null = null) {
      this.isLoading = true
      this.error = null

      // TODO: Figure out how best to avoid duplicate fetches to /directories/:id/contents
      // if (
      //   (directoryId === null && this.currentDirectory === null) ||
      //   (this.currentDirectory && this.currentDirectory._id === directoryId)
      // ) {
      //   console.log(`Already on directory ${directoryId || 'root'}, skipping fetch`)
      //   return this.directoryContents
      // }

      try {
        const contents = await directoryService.getDirectoryContents(directoryId)
        this.directoryContents = contents

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

        return contents
      } catch (error: any) {
        this.error = error.message || 'Failed to fetch directory contents'
        console.error('Error fetching directory contents:', error)
        return null
      } finally {
        this.isLoading = false
      }
    },

    async createDirectory(name: string, parentId: string | null = null) {
      this.isLoading = true
      this.error = null
      try {
        const newDirectory = await directoryService.createDirectory(name, parentId)

        // Check if directory already exists in the state
        const existingIndex = this.directories.findIndex((dir) => dir._id === newDirectory._id)
        if (existingIndex !== -1) {
          // Update existing directory
          this.directories[existingIndex] = newDirectory
        } else {
          // Add new directory
          this.directories.push(newDirectory)
        }

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

        // Update local state - instead of fetching all directories again, just update the moved one
        const index = this.directories.findIndex((dir) => dir._id === directoryId)
        if (index !== -1) {
          this.directories[index] = movedDirectory

          // Also update any child directories that might have changed paths
          const childDirectories = await directoryService.getDirectories(directoryId)
          if (Array.isArray(childDirectories)) {
            // Update existing children or add new ones
            for (const child of childDirectories) {
              const childIndex = this.directories.findIndex((dir) => dir._id === child._id)
              if (childIndex !== -1) {
                this.directories[childIndex] = child
              } else {
                this.directories.push(child)
              }
            }
          }

          // Rebuild the directory tree
          this.directoryTree = buildDirectoryTree(this.directories)
        } else {
          // If we can't find the directory, do a full refresh
          await this.fetchAllDirectories()
        }

        // Refresh contents if we're in the old or new parent directory
        if (
          this.currentDirectory &&
          (this.currentDirectory._id === directoryId ||
            this.currentDirectory._id === newParentId ||
            this.currentDirectory._id === oldParentId)
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
      try {
        await directoryService.moveDocument(documentId, directoryId)
        // Refresh current directory contents
        await this.fetchDirectoryContents(this.currentDirectory?._id || null)
      } catch (error: any) {
        this.error = error.message || 'Failed to move document'
        throw error
      }
    },

    async navigateToDirectory(
      directoryId: string | null,
      options = { updateUrl: true, fetchContent: true }
    ) {
      this.isLoading = true
      this.error = null

      try {
        // Only fetch contents if specified
        if (options.fetchContent) {
          await this.fetchDirectoryContents(directoryId)
        }

        // Only update URL if specified
        if (options.updateUrl) {
          if (directoryId) {
            const directory = this.getDirectoryById(directoryId)
            if (directory) {
              const urlPath = directory.path.replace(/^\//, '')
              router.push({
                name: 'directory',
                params: {
                  path: urlPath || 'root',
                  id: directoryId
                },
                replace: true
              })
            }
          } else {
            router.push({ name: 'home', replace: true })
          }
        }
      } catch (error: any) {
        this.error = error.message || 'Failed to navigate to directory'
        console.error('Error navigating to directory:', error)
      } finally {
        this.isLoading = false
      }
    },

    // Add a new method specifically for route-initiated navigation
    async initializeFromRoute(path: string, id: string | null = null) {
      this.routeInitialized = false

      if (path === '/' || path === '' || !path) {
        // Clear state for root
        this.currentDirectory = null
        this.breadcrumbs = [{ _id: null, name: 'Home', path: '/' }]

        // Fetch root contents with fromRoute=true flag
        await this.navigateToDirectory(null, { updateUrl: true, fetchContent: true })
        return
      }

      if (id) {
        // Use the ID directly if provided (fromRoute=true)
        await this.navigateToDirectory(id, { updateUrl: true, fetchContent: true })
      } else {
        // Find by path as fallback
        const formattedPath = path.startsWith('/') ? path : `/${path}`
        const directory = this.directories.find((dir) => dir.path === formattedPath)

        if (directory) {
          await this.navigateToDirectory(directory._id, { updateUrl: true, fetchContent: true })
        } else {
          // Fallback to root with warning
          console.warn(`Directory with path ${formattedPath} not found, navigating to root`)
          await this.navigateToDirectory(null, { updateUrl: true, fetchContent: true })
        }
      }
    },

    async resetToRoot() {
      // Clear all state first
      this.currentDirectory = null
      this.breadcrumbs = [{ _id: null, name: 'Home', path: '/' }]

      // Force a stop to any pending navigations
      this.isNavigating = false

      // Then explicitly fetch root contents
      this.isLoading = true
      try {
        // Clear directory contents first to avoid flashing incorrect data
        this.directoryContents = null
        await this.fetchDirectoryContents(null)
      } catch (error: any) {
        console.error('Error resetting to root:', error)
      } finally {
        this.isLoading = false
      }
    },

    // Updated to handle URL-based navigation
    async navigateToPath(path: string, id: string | null = null) {
      this.isLoading = true
      this.error = null
      try {
        if (path === '/' || path === '' || path === 'root') {
          return this.navigateToDirectory(null)
        }

        // If we have an ID, use it directly
        if (id) {
          return this.navigateToDirectory(id)
        }

        // Otherwise, try to find the directory by path
        const directory = this.getDirectoryByPath('/' + path)
        if (directory) {
          return this.navigateToDirectory(directory._id)
        }

        // If directory not found, navigate to root
        console.warn(`Directory with path /${path} not found, navigating to root`)
        return this.navigateToDirectory(null)
      } catch (error: any) {
        this.error = error.message || 'Failed to navigate to path'
        console.error('Error navigating to path:', error)
        // Fall back to root directory
        return this.navigateToDirectory(null)
      } finally {
        this.isLoading = false
      }
    }
  }
})
