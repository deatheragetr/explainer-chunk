export interface Directory {
  _id: string
  user_id: string
  name: string
  parent_id: string | null
  path: string
  created_at: string
  updated_at: string
}

export interface DirectoryContents {
  directories: Directory[]
  documents: any[] // Using any for now, but should be replaced with a proper Document type
}

export interface DirectoryBreadcrumb {
  _id: string | null
  name: string
  path: string
}

export interface DirectoryTreeNode {
  _id: string
  name: string
  path: string
  parent_id: string | null
  children: DirectoryTreeNode[]
  isExpanded?: boolean
}

export function buildDirectoryTree(directories: Directory[]): DirectoryTreeNode[] {
  const directoryMap = new Map<string, DirectoryTreeNode>()
  const rootNodes: DirectoryTreeNode[] = []

  // First pass: create all nodes
  directories.forEach((dir) => {
    directoryMap.set(dir._id, {
      _id: dir._id,
      name: dir.name,
      path: dir.path,
      parent_id: dir.parent_id,
      children: [],
      isExpanded: false
    })
  })

  // Second pass: build the tree
  directories.forEach((dir) => {
    const node = directoryMap.get(dir._id)
    if (node) {
      if (dir.parent_id === null) {
        rootNodes.push(node)
      } else {
        const parentNode = directoryMap.get(dir.parent_id)
        if (parentNode) {
          parentNode.children.push(node)
        }
      }
    }
  })

  // Sort nodes by name
  rootNodes.sort((a, b) => a.name.localeCompare(b.name))
  directoryMap.forEach((node) => {
    node.children.sort((a, b) => a.name.localeCompare(b.name))
  })

  return rootNodes
}

export function buildBreadcrumbs(
  currentDirectory: Directory | null,
  directories: Directory[]
): DirectoryBreadcrumb[] {
  if (!currentDirectory) {
    return [{ _id: null, name: 'Home', path: '/' }]
  }

  const breadcrumbs: DirectoryBreadcrumb[] = [{ _id: null, name: 'Home', path: '/' }]
  const pathParts = currentDirectory.path.split('/').filter(Boolean)

  let currentPath = ''
  for (let i = 0; i < pathParts.length; i++) {
    currentPath += '/' + pathParts[i]
    const dir = directories.find((d) => d.path === currentPath)
    if (dir) {
      breadcrumbs.push({
        _id: dir._id,
        name: dir.name,
        path: dir.path
      })
    }
  }

  return breadcrumbs
}
