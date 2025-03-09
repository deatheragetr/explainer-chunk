import axios from './axios'
import type { Directory, DirectoryContents } from '@/types/directory'

export default {
  /**
   * Create a new directory
   * @param name The name of the directory
   * @param parentId The ID of the parent directory (null for root)
   * @returns The created directory
   */
  async createDirectory(name: string, parentId: string | null = null): Promise<Directory> {
    const params = new URLSearchParams()
    params.append('name', name)
    if (parentId) {
      params.append('parent_id', parentId)
    }
    const response = await axios.post(`/directories?${params.toString()}`)
    const dir = response.data
    return { ...dir, _id: dir.id || dir._id }
  },

  /**
   * Get a list of directories
   * @param parentId The ID of the parent directory (null for root)
   * @returns List of directories
   */
  async getDirectories(parentId: string | null = null): Promise<Directory[]> {
    const params = new URLSearchParams()
    if (parentId) {
      params.append('parent_id', parentId)
    }
    const url = `/directories?${params.toString()}`

    try {
      const response = await axios.get(url)

      // The API returns a DirectoryListResponse object with a directories array
      if (response.data && Array.isArray(response.data.directories)) {
        // Map the API response to our expected format
        return response.data.directories.map((dir: any) => ({
          ...dir,
          _id: dir.id || dir._id // Ensure _id is set from id if available
        }))
      } else {
        console.error('Unexpected API response format:', response.data)
        return []
      }
    } catch (error) {
      console.error(`Error fetching directories with parent_id ${parentId}:`, error)
      return []
    }
  },

  /**
   * Get a directory by ID
   * @param directoryId The ID of the directory
   * @returns The directory
   */
  async getDirectory(directoryId: string): Promise<Directory> {
    const response = await axios.get(`/directories/${directoryId}`)
    const dir = response.data
    return { ...dir, _id: dir.id || dir._id }
  },

  /**
   * Get a directory by path
   * @param path The path of the directory
   * @returns The directory
   */
  async getDirectoryByPath(path: string): Promise<Directory> {
    const response = await axios.get(`/directories/path/${path}`)
    const dir = response.data
    return { ...dir, _id: dir.id || dir._id }
  },

  /**
   * Update a directory
   * @param directoryId The ID of the directory
   * @param name The new name of the directory
   * @returns The updated directory
   */
  async updateDirectory(directoryId: string, name: string): Promise<Directory> {
    const params = new URLSearchParams()
    params.append('name', name)
    const response = await axios.put(`/directories/${directoryId}?${params.toString()}`)
    const dir = response.data
    return { ...dir, _id: dir.id || dir._id }
  },

  /**
   * Delete a directory
   * @param directoryId The ID of the directory
   * @param recursive Whether to delete all child directories and documents
   * @returns Success message
   */
  async deleteDirectory(
    directoryId: string,
    recursive: boolean = false
  ): Promise<{ message: string }> {
    const params = new URLSearchParams()
    params.append('recursive', recursive.toString())
    const response = await axios.delete(`/directories/${directoryId}?${params.toString()}`)
    return response.data
  },

  /**
   * Move a directory to a new parent
   * @param directoryId The ID of the directory to move
   * @param newParentId The ID of the new parent directory (null for root)
   * @returns The moved directory
   */
  async moveDirectory(directoryId: string, newParentId: string | null = null): Promise<Directory> {
    const params = new URLSearchParams()
    if (newParentId) {
      params.append('new_parent_id', newParentId)
    }
    const response = await axios.post(`/directories/${directoryId}/move?${params.toString()}`)
    const dir = response.data
    return { ...dir, _id: dir.id || dir._id }
  },

  /**
   * Get the contents of a directory (subdirectories and documents)
   * @param directoryId The ID of the directory (null for root)
   * @returns The directory contents
   */
  async getDirectoryContents(directoryId: string | null = null): Promise<DirectoryContents> {
    const url = directoryId ? `/directories/${directoryId}/contents` : '/directories/root/contents'
    const response = await axios.get(url)

    // Map directories to ensure they have _id
    const contents = response.data
    if (contents && Array.isArray(contents.directories)) {
      contents.directories = contents.directories.map((dir: any) => ({
        ...dir,
        _id: dir.id || dir._id
      }))
    }

    return contents
  },

  /**
   * Move a document to a new directory
   * @param documentId The ID of the document to move
   * @param directoryId The ID of the new directory (null for root)
   * @returns The moved document
   */
  async moveDocument(documentId: string, directoryId: string | null = null): Promise<any> {
    const params = new URLSearchParams()
    if (directoryId) {
      params.append('directory_id', directoryId)
    }
    const response = await axios.post(`/documents/${documentId}/move?${params.toString()}`)
    return response.data
  },

  /**
   * Get all root directories (directories with no parent)
   * Note: This does not return all directories in the system, only the root level ones.
   * To get a complete directory tree, you need to recursively fetch children.
   * @returns List of root directories
   */
  async getAllDirectories(): Promise<Directory[]> {
    // This returns only root directories (where parent_id is null)
    return this.getDirectories(null)
  }
}
