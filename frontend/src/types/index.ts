// Import Progress Status Bar
export interface ImportProgress {
  task_id?: string
  connection_id?: string
  status: string
  progress: number | null
  payload: {
    presigned_url?: string
    file_type?: string
    document_upload_id?: string
    url_friendly_file_name?: string
  }
}

export interface ExtractionResult {
  text: string
  metadata?: Record<string, any>
}
